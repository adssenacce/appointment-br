from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from src.configuracoes.banco_dados import Base


class Usuario(Base):
    """Modelo de Usuário do sistema."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)
    administrador = Column(Boolean, default=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com tenants (um usuário pode pertencer a múltiplos tenants)
    tenants_usuarios = relationship("TenantUsuario", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario(id={self.id}, nome='{self.nome}', email='{self.email}')>"


class TenantUsuario(Base):
    """Tabela associativa entre Tenant e Usuario (many-to-many)."""

    __tablename__ = "tenants_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    administrador_tenant = Column(Boolean, default=False)
    data_vinculo = Column(DateTime, default=datetime.utcnow)

    # Constraints para evitar duplicação
    __table_args__ = (
        UniqueConstraint('tenant_id', 'usuario_id', name='uq_tenant_usuario'),
    )

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="usuarios_tenants")
    usuario = relationship("Usuario", back_populates="tenants_usuarios")

    def __repr__(self):
        return f"<TenantUsuario(tenant_id={self.tenant_id}, usuario_id={self.usuario_id})>"
