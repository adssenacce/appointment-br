from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Table
from sqlalchemy.orm import relationship
from datetime import datetime

from src.configuracoes.banco_dados import Base


class Permissao(Base):
    """Modelo de Permissão do sistema."""

    __tablename__ = "permissoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    recurso = Column(String(100), nullable=False)  # Ex: 'usuarios', 'tenants', 'relatorios'
    acao = Column(String(50), nullable=False)  # Ex: 'criar', 'ler', 'atualizar', 'deletar'
    ativa = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    cargos = relationship("CargoPermissao", back_populates="permissao", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Permissao(id={self.id}, nome='{self.nome}', recurso='{self.recurso}')>"


class Cargo(Base):
    """Modelo de Cargo (Role) do sistema."""

    __tablename__ = "cargos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)  # NULL = cargo global
    descricao = Column(String(255), nullable=True)
    eh_padrao = Column(Boolean, default=False)  # Cargo padrão para novos usuários
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    permissoes_cargos = relationship("CargoPermissao", back_populates="cargo", cascade="all, delete-orphan")
    usuarios_cargos = relationship("UsuarioCargoTenant", back_populates="cargo", cascade="all, delete-orphan")
    tenant = relationship("Tenant", backref="cargos")

    # Constraints
    __table_args__ = (
        UniqueConstraint('slug', 'tenant_id', name='uq_cargo_slug_tenant'),
    )

    def __repr__(self):
        return f"<Cargo(id={self.id}, nome='{self.nome}', slug='{self.slug}')>"


class CargoPermissao(Base):
    """Tabela associativa entre Cargo e Permissao (many-to-many)."""

    __tablename__ = "cargos_permissoes"

    id = Column(Integer, primary_key=True, index=True)
    cargo_id = Column(Integer, ForeignKey("cargos.id"), nullable=False)
    permissao_id = Column(Integer, ForeignKey("permissoes.id"), nullable=False)
    data_vinculo = Column(DateTime, default=datetime.utcnow)

    # Constraints para evitar duplicação
    __table_args__ = (
        UniqueConstraint('cargo_id', 'permissao_id', name='uq_cargo_permissao'),
    )

    # Relacionamentos
    cargo = relationship("Cargo", back_populates="permissoes_cargos")
    permissao = relationship("Permissao", back_populates="cargos")

    def __repr__(self):
        return f"<CargoPermissao(cargo_id={self.cargo_id}, permissao_id={self.permissao_id})>"


class UsuarioCargoTenant(Base):
    """Tabela associativa entre Usuario, Cargo e Tenant (many-to-many com contexto)."""

    __tablename__ = "usuarios_cargos_tenants"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cargo_id = Column(Integer, ForeignKey("cargos.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    data_vinculo = Column(DateTime, default=datetime.utcnow)

    # Constraints para evitar duplicação
    __table_args__ = (
        UniqueConstraint('usuario_id', 'cargo_id', 'tenant_id', name='uq_usuario_cargo_tenant'),
    )

    # Relacionamentos
    usuario = relationship("Usuario", backref="cargos_tenants_usuarios")
    cargo = relationship("Cargo", back_populates="usuarios_cargos")
    tenant = relationship("Tenant", backref="usuarios_cargos_tenants")

    def __repr__(self):
        return f"<UsuarioCargoTenant(usuario_id={self.usuario_id}, cargo_id={self.cargo_id}, tenant_id={self.tenant_id})>"
