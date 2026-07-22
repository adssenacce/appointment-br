from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from src.configuracoes.banco_dados import Base


class Tenant(Base):
    """Modelo de Tenant (Organização)."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tenant(id={self.id}, nome='{self.nome}', slug='{self.slug}')>"
