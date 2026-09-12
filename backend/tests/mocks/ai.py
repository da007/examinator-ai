# tests/mocks/ai.py
import hashlib

class MockEmbedderService:
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        result =[]
        for text in texts:
            seed = int(hashlib.md5(text.encode('utf-8')).hexdigest()[:8], 16)
            vector =[((seed + i) % 100) / 100.0 for i in range(384)]
            norm = sum(x**2 for x in vector) ** 0.5
            normalized_vector =[x / (norm or 1) for x in vector]
            result.append(normalized_vector)
        return result

mock_embedder = MockEmbedderService()