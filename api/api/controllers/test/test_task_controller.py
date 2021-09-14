import sys
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from aiohttp import web_response

with patch('wazuh.common.wazuh_uid'):
    with patch('wazuh.common.wazuh_gid'):
        sys.modules['wazuh.rbac.orm'] = MagicMock()
        import wazuh.rbac.decorators
        from api.controllers.task_controller import get_tasks_status
        from api.controllers.test.utils import CustomMagicMockReturn
        from wazuh import task
        from wazuh.core.common import database_limit
        from wazuh.tests.util import RBAC_bypasser
        wazuh.rbac.decorators.expose_resources = RBAC_bypasser
        del sys.modules['wazuh.rbac.orm']


@pytest.mark.asyncio
@patch('api.controllers.task_controller.DistributedAPI.distribute_function', return_value=AsyncMock())
@patch('api.controllers.task_controller.remove_nones_to_dict')
@patch('api.controllers.task_controller.DistributedAPI.__init__', return_value=None)
@patch('api.controllers.task_controller.raise_if_exc', return_value=CustomMagicMockReturn())
async def test_task_controller(mock_exc, mock_dapi, mock_remove, mock_dfunc, mock_request=MagicMock()):
    """Test all task_controller endpoints"""
    async def test_get_tasks_status():
        f_kwargs = {'select': None,
                    'search': None,
                    'offset': 0,
                    'limit': database_limit,
                    'filters': {
                        'task_list': None,
                        'agent_list': None,
                        'status': None,
                        'module': None,
                        'command': None,
                        'node': None
                        },
                    'sort': None,
                    'q': None
                    }
        result = await get_tasks_status(request=mock_request)
        mock_dapi.assert_called_with(f=task.get_task_status,
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
    functions = [test_get_tasks_status
                 ]
    for test_funct in functions:
        await test_funct()
