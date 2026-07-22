from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from src.configuracoes.banco_dados import obter_sessao_db
from src.utilitarios.autenticacao import obter_usuario_atual
from src.servicos.servico_permissao import ServicoPermissao, ServicoCargo
from src.esquemas.permissao import (
    PermissaoCriacao,
    PermissaoAtualizacao,
    PermissaoResposta,
    CargoCriacao,
    CargoAtualizacao,
    CargoResposta,
    UsuarioCargoVinculo
)
from src.modelos.usuario import Usuario


router = APIRouter(prefix="/api/v1", tags=["Permissões e Cargos"])


def obter_servico_permissao(db: Session = Depends(obter_sessao_db)) -> ServicoPermissao:
    """Dependência para obter o serviço de permissão."""
    return ServicoPermissao(db)


def obter_servico_cargo(db: Session = Depends(obter_sessao_db)) -> ServicoCargo:
    """Dependência para obter o serviço de cargo."""
    return ServicoCargo(db)


# ==================== PERMISSÕES ====================

@router.post("/permissoes", response_model=PermissaoResposta, status_code=status.HTTP_201_CREATED)
def criar_permissao(
    permissao_dados: PermissaoCriacao,
    servico: ServicoPermissao = Depends(obter_servico_permissao),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Cria uma nova permissão.
    
    Requer permissão de administrador global ou do tenant.
    """
    try:
        permissao = servico.criar_permissao(
            nome=permissao_dados.nome,
            recurso=permissao_dados.recurso,
            acao=permissao_dados.acao,
            descricao=permissao_dados.descricao,
            ativa=permissao_dados.ativa
        )
        return permissao
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/permissoes", response_model=List[PermissaoResposta])
def listar_permissoes(
    ativas: Optional[bool] = None,
    servico: ServicoPermissao = Depends(obter_servico_permissao),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Lista todas as permissões disponíveis.
    
    Retorna permissões ativas por padrão.
    """
    return servico.listar_permissoes(ativas=ativas)


@router.get("/permissoes/{permissao_id}", response_model=PermissaoResposta)
def obter_permissao(
    permissao_id: int,
    servico: ServicoPermissao = Depends(obter_servico_permissao),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Obtém detalhes de uma permissão específica."""
    permissao = servico.obter_permissao(permissao_id)
    if not permissao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permissão {permissao_id} não encontrada"
        )
    return permissao


@router.put("/permissoes/{permissao_id}", response_model=PermissaoResposta)
def atualizar_permissao(
    permissao_id: int,
    permissao_dados: PermissaoAtualizacao,
    servico: ServicoPermissao = Depends(obter_servico_permissao),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Atualiza uma permissão existente."""
    dados_dict = permissao_dados.model_dump(exclude_unset=True)
    permissao = servico.atualizar_permissao(permissao_id, **dados_dict)
    if not permissao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permissão {permissao_id} não encontrada"
        )
    return permissao


@router.delete("/permissoes/{permissao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_permissao(
    permissao_id: int,
    servico: ServicoPermissao = Depends(obter_servico_permissao),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Deleta uma permissão."""
    sucesso = servico.deletar_permissao(permissao_id)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permissão {permissao_id} não encontrada"
        )


# ==================== CARGOS ====================

@router.post("/cargos", response_model=CargoResposta, status_code=status.HTTP_201_CREATED)
def criar_cargo(
    cargo_dados: CargoCriacao,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Cria um novo cargo.
    
    Se tenant_id for fornecido, o cargo será específico deste tenant.
    Caso contrário, será um cargo global.
    """
    try:
        cargo = servico.criar_cargo(
            nome=cargo_dados.nome,
            slug=cargo_dados.slug,
            tenant_id=cargo_dados.tenant_id,
            descricao=cargo_dados.descricao,
            eh_padrao=cargo_dados.eh_padrao,
            ativo=cargo_dados.ativo,
            permissoes_ids=cargo_dados.permissoes_ids
        )
        return cargo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/cargos", response_model=List[CargoResposta])
def listar_cargos(
    tenant_id: Optional[int] = None,
    ativos: Optional[bool] = None,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Lista todos os cargos disponíveis.
    
    Se tenant_id for fornecido, retorna cargos globais + cargos do tenant.
    """
    return servico.listar_cargos(tenant_id=tenant_id, ativos=ativos)


@router.get("/cargos/{cargo_id}", response_model=CargoResposta)
def obter_cargo(
    cargo_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Obtém detalhes de um cargo específico."""
    cargo = servico.obter_cargo(cargo_id)
    if not cargo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cargo {cargo_id} não encontrado"
        )
    return cargo


@router.put("/cargos/{cargo_id}", response_model=CargoResposta)
def atualizar_cargo(
    cargo_id: int,
    cargo_dados: CargoAtualizacao,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Atualiza um cargo existente."""
    dados_dict = cargo_dados.model_dump(exclude_unset=True)
    cargo = servico.atualizar_cargo(cargo_id, **dados_dict)
    if not cargo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cargo {cargo_id} não encontrado"
        )
    return cargo


@router.delete("/cargos/{cargo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cargo(
    cargo_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Deleta um cargo."""
    sucesso = servico.deletar_cargo(cargo_id)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cargo {cargo_id} não encontrado"
        )


@router.post("/cargos/{cargo_id}/permissoes/{permissao_id}", status_code=status.HTTP_201_CREATED)
def adicionar_permissao_ao_cargo(
    cargo_id: int,
    permissao_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Adiciona uma permissão a um cargo."""
    try:
        servico.adicionar_permissao_ao_cargo(cargo_id, permissao_id)
        return {"mensagem": "Permissão adicionada ao cargo com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/cargos/{cargo_id}/permissoes/{permissao_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_permissao_do_cargo(
    cargo_id: int,
    permissao_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Remove uma permissão de um cargo."""
    servico.remover_permissao_do_cargo(cargo_id, permissao_id)


# ==================== USUÁRIOS E CARGOS ====================

@router.post("/tenants/{tenant_id}/usuarios/{usuario_id}/cargos", status_code=status.HTTP_201_CREATED)
def atribuir_cargo_a_usuario(
    tenant_id: int,
    usuario_id: int,
    vinculo: UsuarioCargoVinculo,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Atribui um cargo a um usuário em um tenant.
    
    Requer permissão de administrador do tenant.
    """
    try:
        servico.atribuir_cargo_a_usuario(
            usuario_id=usuario_id,
            cargo_id=vinculo.cargo_id,
            tenant_id=tenant_id
        )
        return {"mensagem": f"Cargo {vinculo.cargo_id} atribuído ao usuário {usuario_id} no tenant {tenant_id}"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/tenants/{tenant_id}/usuarios/{usuario_id}/cargos/{cargo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_cargo_de_usuario(
    tenant_id: int,
    usuario_id: int,
    cargo_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Remove um cargo de um usuário em um tenant.
    
    Não permite remover o único administrador do tenant.
    """
    try:
        servico.remover_cargo_de_usuario(usuario_id, cargo_id, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/tenants/{tenant_id}/usuarios/{usuario_id}/cargos")
def listar_cargos_do_usuario(
    tenant_id: int,
    usuario_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Lista todos os cargos de um usuário em um tenant."""
    cargos = servico.listar_cargos_do_usuario(usuario_id, tenant_id)
    return {"cargos": cargos}


@router.get("/tenants/{tenant_id}/usuarios/{usuario_id}/permissoes")
def listar_permissoes_do_usuario(
    tenant_id: int,
    usuario_id: int,
    servico: ServicoCargo = Depends(obter_servico_cargo),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Lista todas as permissões de um usuário em um tenant."""
    permissoes = servico.listar_permissoes_do_usuario(usuario_id, tenant_id)
    return {"permissoes": permissoes}
