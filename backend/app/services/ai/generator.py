import json
import re
import asyncio
import logging
import httpx
from typing import List, Type
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.llm_schemas import QuestionsData, ReferenceData, AIResultLabel

logger = logging.getLogger(__name__)

class JSONCleaner:
    """Утилита для надежного извлечения JSON из ответов LLM."""
    
    @staticmethod
    def get_candidates(text: str) -> List[str]:
        candidates =[]
        md_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        candidates.extend(md_blocks)
        
        greedy_obj = re.search(r'\{[\s\S]*\}', text)
        if greedy_obj: candidates.append(greedy_obj.group(0))
            
        greedy_arr = re.search(r'\[[\s\S]*\]', text)
        if greedy_arr: candidates.append(greedy_arr.group(0))

        candidates.append(text)
        
        seen = set()
        unique_candidates =[]
        for c in candidates:
            c_stripped = c.strip()
            if c_stripped and c_stripped not in seen:
                seen.add(c_stripped)
                unique_candidates.append(c_stripped)
        return unique_candidates

    @staticmethod
    def apply_fixes(text: str) -> str:
        text = text.replace("“", '"').replace("”", '"')
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        text = re.sub(r'\bNone\b', 'null', text)
        
        def escape_newlines(match):
            return match.group(0).replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        text = re.sub(r'"(?:\\.|[^"\\])*"', escape_newlines, text, flags=re.DOTALL)
        
        text = re.sub(r'([\"\]\}])\s*\n?\s*(?=\")', r'\1, ', text)
        text = re.sub(r',\s*([\]\}])', r'\1', text)
        return text

    @staticmethod
    def apply_aggressive_fixes(text: str) -> str:
        text = text.replace('\n', ' ')
        text = re.sub(r',\s*,', ',', text)
        return text


class LMStudioAdapter:
    """
    Адаптер для LM Studio (OpenAI-совместимый локальный сервер).
    Реализует модули AGE и HGC(Layer 4) из TDD.
    Запустите LM Studio → вкладка Local Server → Start Server (порт 1234).
    """
    def __init__(self):
        self.base_url = settings.lmStudio.BASE_URL
        self.model = settings.lmStudio.MODEL
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _request(self, user_prompt: str, temp: float, response_model: Type[BaseModel]) -> BaseModel:
        max_attempts = 3
        # LM Studio: стандартный OpenAI-совместимый путь
        endpoint = f"{self.base_url}/v1/chat/completions"
        
        logger.info(f"LM Studio: подключение к {endpoint}")

        payload = {
            "model": settings.lmStudio.MODEL,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temp
        }

        # Настройка клиента для принудительного использования IPv4
        # Это решает проблему ConnectError на Windows/WSL2
        async with httpx.AsyncClient(
            timeout=90.0,
            # Форсируем IPv4 через транспорт
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        ) as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = await client.post(
                        endpoint, 
                        json=payload, 
                        headers=self.headers
                    )
                    
                    if response.status_code == 403:
                        logger.error("LM Studio: доступ запрещён (403). Проверьте BASE_URL и запущен ли сервер.")
                    
                    response.raise_for_status()
                    
                    raw_content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Логика очистки JSON (твой JSONCleaner)
                    candidates = JSONCleaner.get_candidates(raw_content)
                    for candidate in candidates:
                        try:
                            cleaned = JSONCleaner.apply_fixes(candidate)
                            return response_model.model_validate_json(cleaned)
                        except ValidationError:
                            try:
                                aggressive = JSONCleaner.apply_aggressive_fixes(cleaned)
                                return response_model.model_validate_json(aggressive)
                            except ValidationError:
                                pass
                    
                    raise ValueError("Could not find valid JSON in LLM response")

                except Exception as e:
                    logger.warning(f"LLM Attempt {attempt} failed: {str(e)}")
                    if attempt == max_attempts:
                        raise e
                    await asyncio.sleep(2 ** attempt)

    # ==========================================
    # MODULE: AGE (AI Generation Engine) - QGen
    # ==========================================
    async def generate_questions(self, chunk_text: str) -> QuestionsData:
        """Генерирует вопросы на основе конкретного абзаца/чанка лекции."""
        prompt = (            
f"""
TEXT CHUNK:
{chunk_text}

TASK:
Generate 1 to 3 open-ended questions based strictly on this text chunk.

RULES:
- Questions must require understanding, not just copy-pasting.
- Do NOT reference the text explicitly (e.g., "As mentioned in the text...").
- Language: Russian.
- Return ONLY valid JSON matching this format: {{"questions": ["q1", "q2"]}}
"""
        )
        return await self._request(prompt, temp=0.3, response_model=QuestionsData)

    # ==========================================
    # MODULE: AGE (AI Generation Engine) - AGen & TGen
    # ==========================================
    async def generate_reference(self, question: str, chunk_text: str) -> ReferenceData:
        """Генерирует эталонный ответ и извлекает тезисы."""
        prompt = (
f"""
TEXT CHUNK:
{chunk_text}

QUESTION:
{question}

TASK:
1. Write a complete reference answer to the question based ONLY on the text chunk.
2. Extract 2-4 key theses from your answer (assign importance 1 to 3).

RULES:
- Language: Russian.
- Return ONLY valid JSON matching this format: 
{{
  "reference_answer": "text", 
  "key_theses": [{{"text": "thesis", "importance": 3}}]
}}
"""
        )
        return await self._request(prompt, temp=0.2, response_model=ReferenceData)

    # ==========================================
    # MODULE: HGC (Hybrid Grading Core) - Layer 4
    # ==========================================
    async def evaluate_answer(self, question: str, reference: str, student_answer: str) -> AIResultLabel:
        """
        Layer 4: Semantic Arbitrage. 
        Классификация ответа студента (Few-shot prompt). Модель не ставит балл, а дает метку.
        """
        prompt = (
f"""
ROLE: You are an impartial AI grader.
TASK: Classify the student's answer compared to the reference answer.

QUESTION: {question}
REFERENCE: {reference}
STUDENT ANSWER: {student_answer}

RULES:
1. Choose ONE label: "correct", "partially_correct", or "wrong".
2. "correct": Covers main points, no critical errors.
3. "partially_correct": Missing important details or contains minor errors.
4. "wrong": Fundamentally incorrect, off-topic, or completely hallucinated facts.
5. Provide a confidence_delta (0.0 to 1.0) indicating how sure you are.
6. DO NOT provide any explanations, feedback, or additional text.

Return ONLY valid JSON matching this format:
{{"label": "correct", "confidence_delta": 0.95}}
"""
        )
        return await self._request(prompt, temp=0.1, response_model=AIResultLabel)

llm_generator = LMStudioAdapter()