"""Controlador para gerenciamento de Usuários no contexto do Tenant."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from src.configuracoes.banco_dados import obter_sessao
from src.esquemas.usuario import (
    UsuarioResposta,
    UsuarioComTenantsResposta,
    TenantUsuarioVinculo
)
from src.servicos.servico_autenticacao import ServicoUsuario, ServicoAutenticacao
from src.controladores.controlador_autenticacao import obter_usuario_atual
from src.modelos.usuario import Usuario, TenantUsuario
from src.modelos.tenant import Tenant

router = APIRouter(prefix="/api/v1", tags=["Usuários por Tenant"])


def _obter_servico_usuario(sessao: Session = Depends(obter_sessao)) -> ServicoUsuario:
    """Dependency para obter serviço de usuário."""
    return ServicoUsuario(sessao)


def _obter_servico_autenticacao(sessao: Session = Depends(obter_sessao)) -> ServicoAutenticacao:
    """Dependency para obter serviço de autenticação."""
    return ServicoAutenticacao(sessao)


@router.get(
    "/tenants/{tenant_id}/usuarios",
    response_model=List[UsuarioComTenantsResposta],
    summary="Listar usuários de um tenant"
)
async def listar_usuarios_do_tenant(
    tenant_id: int,
    ativo: bool = Query(None, description="Filtrar por status ativo/inativo"),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao)
):
    """
    Lista todos os usuários vinculados a um tenant específico.
    
    Requer autenticação e que o usuário atual pertença ao tenant.
    Apenas administradores do tenant podem listar todos os usuários.
    """
    # Verifica se é administrador global (tem acesso a todos os tenants)
    eh_admin_global = usuario_atual.administrador
    
    # Verifica se usuário atual pertence ao tenant (se não for admin global)
    if not eh_admin_global:
        vinculo_usuario = sessao.query(TenantUsuario).filter(
            TenantUsuario.usuario_id == usuario_atual.id,
            TenantUsuario.tenant_id == tenant_id
        ).first()
        
        if not vinculo_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Você não pertence a este tenant."
            )
    
    # Verifica se é administrador do tenant (ou administrador global)
    if eh_admin_global:
        eh_admin_tenant = True
    else:
        vinculo_usuario = sessao.query(TenantUsuario).filter(
            TenantUsuario.usuario_id == usuario_atual.id,
            TenantUsuario.tenant_id == tenant_id
        ).first()
        eh_admin_tenant = vinculo_usuario.administrador_tenant if vinculo_usuario else False
    
    # Busca todos os vínculos de usuários neste tenant
    vinculos = sessao.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == tenant_id
    ).all()
    
    usuarios_ids = [v.usuario_id for v in vinculos]
    
    # Filtra usuários
    consulta_usuarios = sessao.query(Usuario).filter(Usuario.id.in_(usuarios_ids))
    
    if ativo is not None:
        consulta_usuarios = consulta_usuarios.filter(Usuario.ativo == ativo)
    
    usuarios = consulta_usuarios.all()
    
    # Monta resposta com informações do vínculo
    resultado = []
    for usuario in usuarios:
        vinculo = next(v for v in vinculos if v.usuario_id == usuario.id)
        
        # Usuários comuns só veem a si mesmos
        if not eh_admin_tenant and usuario.id != usuario_atual.id:
            continue
        
        tenants_info = [{
            "tenant_id": vinculo.tenant_id,
            "administrador_tenant": vinculo.administrador_tenant,
            "data_vinculo": vinculo.data_vinculo
        }]
        
        resultado.append(UsuarioComTenantsResposta(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            ativo=usuario.ativo,
            administrador=usuario.administrador,
            data_criacao=usuario.data_criacao,
            data_atualizacao=usuario.data_atualizacao,
            tenants=tenants_info
        ))
    
    return resultado


@router.post(
    "/tenants/{tenant_id}/usuarios/{usuario_id}",
    summary="Adicionar usuário a um tenant",
    response_model=dict
)
async def adicionar_usuario_a_tenant(
    tenant_id: int,
    usuario_id: int,
    dados: TenantUsuarioVinculo,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao)
):
    """
    Adiciona um usuário existente a um tenant.
    
    Requer que:
    - Usuário atual seja administrador do tenant ou administrador global
    - Usuário a ser adicionado exista
    - Tenant exista
    - Usuário ainda não esteja vinculado ao tenant
    """
    # Verifica se usuário atual tem permissão
    vinculo_usuario_atual = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_atual.id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario_atual and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores do tenant podem adicionar usuários."
        )
    
    if vinculo_usuario_atual and not vinculo_usuario_atual.administrador_tenant and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores do tenant podem adicionar usuários."
        )
    
    # Verifica se tenant existe
    tenant = sessao.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} não encontrado"
        )
    
    # Verifica se usuário existe
    usuario = sessao.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {usuario_id} não encontrado"
        )
    
    # Verifica se já está vinculado
    vinculo_existente = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if vinculo_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Usuário {usuario_id} já está vinculado ao tenant {tenant_id}"
        )
    
    # Cria vínculo
    novo_vinculo = TenantUsuario(
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        administrador_tenant=dados.administrador_tenant
    )
    
    sessao.add(novo_vinculo)
    sessao.commit()
    
    return {
        "mensagem": f"Usuário {usuario_id} adicionado ao tenant {tenant_id} com sucesso",
        "usuario_id": usuario_id,
        "tenant_id": tenant_id,
        "administrador_tenant": dados.administrador_tenant
    }


@router.delete(
    "/tenants/{tenant_id}/usuarios/{usuario_id}",
    summary="Remover usuário de um tenant",
    response_model=dict
)
async def remover_usuario_de_tenant(
    tenant_id: int,
    usuario_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao)
):
    """
    Remove um usuário de um tenant.
    
    Requer que:
    - Usuário atual seja administrador do tenant ou administrador global
    - Não seja o último administrador do tenant (regra de negócio)
    - Usuário não possa ser removido de si mesmo
    """
    # Verifica se está tentando remover a si mesmo
    if usuario_id == usuario_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não pode remover a si mesmo do tenant"
        )
    
    # Verifica se usuário atual tem permissão
    vinculo_usuario_atual = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_atual.id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario_atual and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você não pertence a este tenant."
        )
    
    if vinculo_usuario_atual and not vinculo_usuario_atual.administrador_tenant and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores do tenant podem remover usuários."
        )
    
    # Verifica se usuário está vinculado ao tenant
    vinculo_usuario = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {usuario_id} não está vinculado ao tenant {tenant_id}"
        )
    
    # REGRA DE NEGÓCIO: Não permitir remover o último administrador do tenant
    # Conta quantos administradores existem neste tenant
    administradores = sessao.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.administrador_tenant == True
    ).all()
    
    # Se o usuário a ser removido é administrador e é o único, impede
    if vinculo_usuario.administrador_tenant and len(administradores) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o último administrador do tenant. Adicione outro administrador primeiro."
        )
    
    # Remove vínculo
    sessao.delete(vinculo_usuario)
    sessao.commit()
    
    return {
        "mensagem": f"Usuário {usuario_id} removido do tenant {tenant_id} com sucesso"
    }


@router.put(
    "/tenants/{tenant_id}/usuarios/{usuario_id}/permissoes",
    summary="Atualizar permissões de usuário no tenant",
    response_model=dict
)
async def atualizar_permissoes_usuario_no_tenant(
    tenant_id: int,
    usuario_id: int,
    dados: TenantUsuarioVinculo,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao)
):
    """
    Atualiza as permissões de um usuário em um tenant (ex: tornar administrador).
    
    Requer que:
    - Usuário atual seja administrador do tenant ou administrador global
    - Usuário esteja vinculado ao tenant
    - Não remova o último administrador (se estiver despromovendo)
    """
    # Verifica se usuário atual tem permissão
    vinculo_usuario_atual = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_atual.id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario_atual and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você não pertence a este tenant."
        )
    
    if vinculo_usuario_atual and not vinculo_usuario_atual.administrador_tenant and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores do tenant podem alterar permissões."
        )
    
    # Verifica se usuário está vinculado ao tenant
    vinculo_usuario = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {usuario_id} não está vinculado ao tenant {tenant_id}"
        )
    
    # REGRA DE NEGÓCIO: Não permitir remover o último administrador
    if vinculo_usuario.administrador_tenant and not dados.administrador_tenant:
        # Conta quantos administradores existem neste tenant
        administradores = sessao.query(TenantUsuario).filter(
            TenantUsuario.tenant_id == tenant_id,
            TenantUsuario.administrador_tenant == True
        ).all()
        
        if len(administradores) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível remover o último administrador do tenant. Adicione outro administrador primeiro."
            )
    
    # Atualiza permissões
    vinculo_usuario.administrador_tenant = dados.administrador_tenant
    sessao.flush()
    sessao.commit()
    
    return {
        "mensagem": f"Permissões do usuário {usuario_id} atualizadas no tenant {tenant_id}",
        "usuario_id": usuario_id,
        "tenant_id": tenant_id,
        "administrador_tenant": dados.administrador_tenant
    }


@router.get(
    "/tenants/{tenant_id}/usuarios/{usuario_id}",
    response_model=UsuarioComTenantsResposta,
    summary="Buscar usuário específico em um tenant"
)
async def buscar_usuario_no_tenant(
    tenant_id: int,
    usuario_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao)
):
    """
    Busca um usuário específico dentro de um tenant.
    
    Requer que:
    - Usuário atual pertença ao tenant
    - Usuário buscado esteja vinculado ao tenant
    """
    # Verifica se usuário atual pertence ao tenant
    vinculo_usuario_atual = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_atual.id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario_atual:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você não pertence a este tenant."
        )
    
    # Busca usuário no tenant
    vinculo_usuario = sessao.query(TenantUsuario).filter(
        TenantUsuario.usuario_id == usuario_id,
        TenantUsuario.tenant_id == tenant_id
    ).first()
    
    if not vinculo_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {usuario_id} não está vinculado ao tenant {tenant_id}"
        )
    
    # Busca dados do usuário
    usuario = sessao.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {usuario_id} não encontrado"
        )
    
    tenants_info = [{
        "tenant_id": vinculo_usuario.tenant_id,
        "administrador_tenant": vinculo_usuario.administrador_tenant,
        "data_vinculo": vinculo_usuario.data_vinculo
    }]
    
    return UsuarioComTenantsResposta(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        ativo=usuario.ativo,
        administrador=usuario.administrador,
        data_criacao=usuario.data_criacao,
        data_atualizacao=usuario.data_atualizacao,
        tenants=tenants_info
    )
