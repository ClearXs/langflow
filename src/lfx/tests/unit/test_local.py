import lfx.locale
import i18n


def test_read_local_translation():
    assert i18n.t('components.data.api_request.display_name') == 'API Request'
