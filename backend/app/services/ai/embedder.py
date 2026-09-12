import logging
from typing import List

logger = logging.getLogger(__name__)


class EmbedderService:
    """
    Сервис для генерации векторных представлений текста.
    Использует модель multilingual-e5-small (размерность 384).
    Torch и sentence_transformers загружаются только при первом реальном вызове.
    """

    def __init__(self):
        self.device = "cpu"
        self.model_name = "intfloat/multilingual-e5-small"
        self._model = None

    @property
    def model(self):
        """Ленивая загрузка модели и зависимостей при первом обращении."""
        if self._model is None:
            # Импорты здесь — torch не грузится при импорте модуля
            from sentence_transformers import SentenceTransformer  # noqa

            logger.info(
                f"Loading embedding model {self.model_name} on {self.device}..."
            )
            self._model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Embedding model loaded successfully.")
        return self._model

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Превращает список текстов в список векторов.
        E5 требует префикс 'passage:' для индексирования.
        """
        prefixed = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(prefixed, normalize_embeddings=True)
        return embeddings.tolist()

    def get_query_embedding(self, query: str) -> List[float]:
        """Для поиска используем префикс 'query:'."""
        embedding = self.model.encode(f"query: {query}", normalize_embeddings=True)
        return embedding.tolist()


# Синглтон для воркеров и продакшена.
# Создание инстанса дешёвое — torch не грузится до первого get_embeddings().
embedder = EmbedderService()