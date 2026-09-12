import asyncio
import uuid
import os
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_maker
from app.db.base import Base
from app.models import User, Subject, Lecture, UserRole
from app.core.security import get_password_hash
from app.core.config import settings
from app.services.lecture_service import lecture_service
from app.worker.tasks import process_lecture_task

# --- КОНФИГУРАЦИЯ ---
BASE_DIR = Path("manage_data")
AUTO_BACKUP = True  # Флаг обязательного бэкапа
LOG_LEVEL = logging.INFO

logging.basicConfig(level=LOG_LEVEL, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    pass

async def create_backup(db: AsyncSession):
    """Создает JSON-слепок текущих данных пользователей и предметов."""
    if not AUTO_BACKUP:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BASE_DIR / "backups" / f"backup_{timestamp}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"users": [], "subjects": []}
    
    users = (await db.execute(select(User))).scalars().all()
    for u in users:
        data["users"].append({
            "email": u.email, "full_name": u.full_name, "role": u.role, "org_id": str(u.org_id)
        })
    
    subjects = (await db.execute(select(Subject))).scalars().all()
    for s in subjects:
        data["subjects"].append({
            "name": s.name, "teacher_id": str(s.teacher_id), "org_id": str(s.org_id)
        })

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [🏠] Бэкап создан: {backup_path.name}")

def read_csv(file_path: Path) -> List[Dict[str, str]]:
    if not file_path.exists():
        return []
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        # Очищаем все ключи и значения от случайных пробелов и переносов строк
        return [{k.strip(): str(v).strip() for k, v in row.items() if k is not None} for row in reader]

async def handle_users(db: AsyncSession, mode: str, org_id: uuid.UUID):
    csv_path = BASE_DIR / mode / "users.csv"
    rows = read_csv(csv_path)
    if not rows: return

    for row in rows:
        res = await db.execute(select(User).where(User.email == row['email']))
        existing = res.scalar_one_or_none()

        if mode == "to_add":
            if existing:
                # Проверка: если пытаемся добавить существующего, но данные другие
                for field in ['full_name', 'role']:
                    if field in row and str(getattr(existing, field)) != row[field]:
                        raise DataValidationError(f"Конфликт данных для {row['email']}: поле {field} в базе '{getattr(existing, field)}', в CSV '{row[field]}'")
                print(f"  [~] Студент {row['email']} уже существует, пропускаем.")
            else:
                print(f"  [+] Добавление пользователя: {row['email']}")
                new_user = User(
                    email=row['email'],
                    hashed_password=get_password_hash(row.get('password', 'temp_pass_123')),
                    full_name=row.get('full_name'),
                    role=UserRole(row['role']),
                    org_id=org_id,
                    is_active=True
                )
                db.add(new_user)
                await db.flush() # <--- ПРИНУДИТЕЛЬНАЯ ЗАПИСЬ СРАЗУ

        elif mode == "to_update":
            if not existing:
                raise DataValidationError(f"Ошибка обновления: пользователь {row['email']} не найден")
            print(f"  [*] Обновление пользователя: {row['email']}")
            if 'full_name' in row: existing.full_name = row['full_name']
            if 'role' in row: existing.role = UserRole(row['role'])

        elif mode == "to_delete":
            if existing:
                print(f"  [-] Удаление пользователя: {row['email']}")
                await db.execute(delete(User).where(User.id == existing.id))

async def handle_subjects_and_lectures(db: AsyncSession, mode: str, org_id: uuid.UUID):
    csv_path = BASE_DIR / mode / "subjects.csv"
    rows = read_csv(csv_path)
    if not rows: return

    for row in rows:
        res = await db.execute(select(Subject).where(Subject.name == row['name']))
        existing = res.scalar_one_or_none()

        if mode == "to_add":
            if existing:
                if 'description' in row and existing.description != row['description']:
                    raise DataValidationError(f"Предмет {row['name']} уже существует с другим описанием!")
                subject = existing
            else:
                print(f"  [+] Добавление предмета: {row['name']}")
                t_res = await db.execute(select(User).where(User.email == row['teacher_email']))
                teacher = t_res.scalar_one_or_none()
                if not teacher: 
                    raise DataValidationError(f"Учитель '{row['teacher_email']}' не найден для предмета '{row['name']}'")
                
                subject = Subject(name=row['name'], description=row.get('description'), org_id=org_id, teacher_id=teacher.id)
                db.add(subject)
                await db.flush() # <--- ПРИНУДИТЕЛЬНАЯ ЗАПИСЬ СРАЗУ

            # Обработка лекций для этого предмета (только при добавлении/обновлении)
            if 'lecture_folder' in row:
                lecture_path = BASE_DIR / "lectures" / row['lecture_folder']
                if lecture_path.exists():
                    for file in lecture_path.glob("*"):
                        if file.suffix.lower() in ['.docx', '.txt']:
                            l_check = await db.execute(select(Lecture).where(Lecture.title == file.stem))
                            if not l_check.scalar_one_or_none():
                                print(f"    [↑] Загрузка лекции: {file.name}")
                                with open(file, "rb") as f: content = f.read()
                                from app.schemas.lecture import LectureCreate
                                db_l = await lecture_service.create_with_file(db, obj_in=LectureCreate(title=file.stem, org_id=org_id, subject_id=subject.id), 
                                                                              teacher_id=subject.teacher_id, file_content=content, extension=file.suffix[1:])
                                process_lecture_task.delay(str(db_l.id), f"{db_l.org_id}/{db_l.id}{file.suffix.lower()}")

async def main_menu():
    print("\n=== EXAMINATOR AI: SYSTEM MANAGER ===")
    print("1. Применить ДОБАВЛЕНИЯ (to_add/)")
    print("2. Применить ОБНОВЛЕНИЯ (to_update/)")
    print("3. Применить УДАЛЕНИЯ (to_delete/)")
    print("0. Выход")
    
    choice = input("\nВыберите действие: ")
    modes = {"1": "to_add", "2": "to_update", "3": "to_delete"}
    
    if choice not in modes: return

    mode = modes[choice]
    org_id = uuid.UUID(settings.init.SUPERUSER_ORG_ID)
    session_maker = get_session_maker()

    try:
        async with session_maker() as db:
            await create_backup(db)
            print(f"\n🚀 Обработка режима: {mode}...")
            
            await handle_users(db, mode, org_id)
            await db.flush() 
            
            await handle_subjects_and_lectures(db, mode, org_id)
            
            await db.commit()
            print(f"\n✅ Успешно завершено!")
    except DataValidationError as e:
        print(f"\n❌ ОШИБКА ВАЛИДАЦИИ: {e}")
        print("🛑 Изменения не применены.")
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main_menu())