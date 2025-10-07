from pathlib import Path
import i18n

default_lang = "en"

i18n.set('file_format', 'json')
i18n.set('locale', default_lang)
i18n.set('fallback', default_lang)
i18n.set('use_locale_dirs', True)
i18n.set("filename_format", "{namespace}.{format}")
i18n.set("skip_locale_root_data", True)
i18n.load_path.append(str(Path(__file__).parent.resolve() / "translations"))


def set_lang(locale: str):
    i18n.set('locale', locale)


def get_lang():
    return i18n.get('locale')


def get(key: str):
    return i18n.t(key)
