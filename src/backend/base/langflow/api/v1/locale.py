from fastapi import APIRouter
from lfx.locale import set_lang, get_lang, get as t

from langflow.api.v1.schemas import SwitchLocaleRequest

router = APIRouter(prefix="/locale", tags=["Locale"])


@router.put('/switch')
def switch(payload: SwitchLocaleRequest):

    lang = payload.lang

    if lang != get_lang():

        set_lang(payload.lang)

        # clear component cache
        from langflow.interface.components import component_cache

        component_cache.all_types_dict = None


@router.get("/current")
def get_current_locale():
    return get_lang()


@router.get("/{key}")
def get(key: str):
    return t(key)
