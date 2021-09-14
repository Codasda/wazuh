import sys
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from aiohttp import web_response
from connexion.lifecycle import ConnexionResponse

with patch('wazuh.common.wazuh_uid'):
    with patch('wazuh.common.wazuh_gid'):
        with patch('api.configuration.api_conf'):
            sys.modules['wazuh.rbac.orm'] = MagicMock()
            import wazuh.rbac.decorators
            from api.controllers.rule_controller import (delete_file, get_file,
                                                         get_rules,
                                                         get_rules_files,
                                                         get_rules_groups,
                                                         get_rules_requirement,
                                                         put_file)
            from api.controllers.test.utils import CustomMagicMockReturn
            from wazuh import rule as rule_framework
            from wazuh.tests.util import RBAC_bypasser
            wazuh.rbac.decorators.expose_resources = RBAC_bypasser
            del sys.modules['wazuh.rbac.orm']


@pytest.mark.asyncio
@patch('api.controllers.rule_controller.DistributedAPI.distribute_function', return_value=AsyncMock())
@patch('api.controllers.rule_controller.remove_nones_to_dict')
@patch('api.controllers.rule_controller.DistributedAPI.__init__', return_value=None)
@patch('api.controllers.rule_controller.raise_if_exc', return_value=CustomMagicMockReturn())
@pytest.mark.parametrize('mock_bool', [True, False])
async def test_rule_controller(mock_exc, mock_dapi, mock_remove, mock_dfunc, mock_bool, mock_request=MagicMock()):
    """Test all rule_controller endpoints"""
    async def test_get_rules():
        f_kwargs = {'rule_ids': None,
                    'offset': 0,
                    'limit': None,
                    'select': None,
                    'sort_by': ['id'],
                    'sort_ascending': True,
                    'search_text': None,
                    'complementary_search': None,
                    'q': None,
                    'status': None,
                    'group': None,
                    'level': None,
                    'filename': None,
                    'relative_dirname': None,
                    'pci_dss': None,
                    'gdpr': None,
                    'gpg13': None,
                    'hipaa': None,
                    'nist_800_53': mock_request.query.get('nist-800-53', None),
                    'tsc': None,
                    'mitre': None
                    }
        result = await get_rules(request=mock_request)
        mock_dapi.assert_called_with(f=rule_framework.get_rules,
                                     f_kwargs=mock_remove.return_value,
                                     request_type='local_any',
                                     is_async=False,
                                     wait_for_complete=False,
                                     logger=ANY,
                                     rbac_permissions=mock_request['token_info']['rbac_policies']
                                     )
        mock_exc.assert_called_with(mock_dfunc.return_value)
        mock_remove.assert_called_with(f_kwargs)
        assert isinstance(result, web_response.Response)

    async def test_get_rules_groups():
        f_kwargs = {'offset': 0,
                    'limit': None,
                    'sort_by': [''],
                    'sort_ascending': True,
                    'search_text': None,
                    'complementary_search': None
                    }
        result = await get_rules_groups(request=mock_request)
        mock_dapi.assert_called_with(f=rule_framework.get_groups,
                                     f_kwargs=mock_remove.return_value,
                                     request_type='local_any',
                                     is_async=False,
                                     wait_for_complete=False,
                                     logger=ANY,
                                     rbac_permissions=mock_request['token_info']['rbac_policies']
                                     )
        mock_exc.assert_called_with(mock_dfunc.return_value)
        mock_remove.assert_called_with(f_kwargs)
        assert isinstance(result, web_response.Response)

    async def test_get_rules_requirement():
        f_kwargs = {'requirement': '_',
                    'sort_by': [''],
                    'sort_ascending': True,
                    'search_text': None,
                    'complementary_search': None,
                    'offset': 0,
                    'limit': None
                    }
        result = await get_rules_requirement(request=mock_request,
                                             requirement='-')
        mock_dapi.assert_called_with(f=rule_framework.get_requirement,
                                     f_kwargs=mock_remove.return_value,
                                     request_type='local_any',
                                     is_async=False,
                                     wait_for_complete=False,
                                     logger=ANY,
                                     rbac_permissions=mock_request['token_info']['rbac_policies']
                                     )
        mock_exc.assert_called_with(mock_dfunc.return_value)
        mock_remove.assert_called_with(f_kwargs)
        assert isinstance(result, web_response.Response)

    async def test_get_rules_files():
        f_kwargs = {'offset': 0,
                    'limit': None,
                    'sort_by': ['filename'],
                    'sort_ascending': True,
                    'search_text': None,
                    'complementary_search': None,
                    'status': None,
                    'filename': None,
                    'relative_dirname': None
                    }
        result = await get_rules_files(request=mock_request)
        mock_dapi.assert_called_with(f=rule_framework.get_rules_files,
                                     f_kwargs=mock_remove.return_value,
                                     request_type='local_any',
                                     is_async=False,
                                     wait_for_complete=False,
                                     logger=ANY,
                                     rbac_permissions=mock_request['token_info']['rbac_policies']
                                     )
        mock_exc.assert_called_with(mock_dfunc.return_value)
        mock_remove.assert_called_with(f_kwargs)
        assert isinstance(result, web_response.Response)

    async def test_get_file():
        with patch('api.controllers.rule_controller.isinstance', return_value=mock_bool) as mock_isinstance:
            f_kwargs = {'filename': None,
                        'raw': False
                        }
            result = await get_file(request=mock_request)
            mock_dapi.assert_called_with(f=rule_framework.get_rule_file,
                                         f_kwargs=mock_remove.return_value,
                                         request_type='local_master',
                                         is_async=False,
                                         wait_for_complete=False,
                                         logger=ANY,
                                         rbac_permissions=mock_request['token_info']['rbac_policies']
                                         )
            mock_exc.assert_called_with(mock_dfunc.return_value)
            mock_remove.assert_called_with(f_kwargs)
            if mock_isinstance.return_value:
                assert isinstance(result, web_response.Response)
            else:
                assert isinstance(result, ConnexionResponse)

    async def test_put_file():
        with patch('api.controllers.rule_controller.Body.validate_content_type'):
            with patch('api.controllers.rule_controller.Body.decode_body', return_value={}):
                f_kwargs = {'filename': None,
                            'overwrite': False,
                            'content': {}
                            }
                result = await put_file(request=mock_request,
                                        body={})
                mock_dapi.assert_called_with(f=rule_framework.upload_rule_file,
                                             f_kwargs=mock_remove.return_value,
                                             request_type='local_master',
                                             is_async=False,
                                             wait_for_complete=False,
                                             logger=ANY,
                                             rbac_permissions=mock_request['token_info']['rbac_policies']
                                             )
                mock_exc.assert_called_with(mock_dfunc.return_value)
                mock_remove.assert_called_with(f_kwargs)
                assert isinstance(result, web_response.Response)

    async def test_delete_file():
        f_kwargs = {'filename': None
                    }
        result = await delete_file(request=mock_request)
        mock_dapi.assert_called_with(f=rule_framework.delete_rule_file,
                                     f_kwargs=mock_remove.return_value,
                                     request_type='local_master',
                                     is_async=False,
                                     wait_for_complete=False,
                                     logger=ANY,
                                     rbac_permissions=mock_request['token_info']['rbac_policies']
                                     )
        mock_exc.assert_called_with(mock_dfunc.return_value)
        mock_remove.assert_called_with(f_kwargs)
        assert isinstance(result, web_response.Response)

    # Function list containing all sub tests declared above.
    functions = [test_get_rules,
                 test_get_rules_groups,
                 test_get_rules_requirement,
                 test_get_rules_files,
                 test_get_file,
                 test_put_file,
                 test_delete_file
                 ]
    for test_funct in functions:
        await test_funct()
