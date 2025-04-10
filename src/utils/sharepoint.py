"""
SharePoint Context Utilities

Provides functions for interacting with SharePoint using Office365-REST-Python-Client.
"""

import os
import sys
import traceback
from urllib.parse import urljoin
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.listitems.listitem import ListItem

from .config import get_config
from .logging import get_logger

logger = get_logger(__name__)
config = get_config()

def get_sharepoint_context():
    """
    Create a SharePoint client context for authentication and API interactions.

    Returns:
        ClientContext: Authenticated SharePoint client context
    """
    try:
        # Отладочная информация
        print("SharePoint Authentication Details:")
        print(f"Site URL: {config.sharepoint.site_url}")
        print(f"Username: {config.sharepoint.username}")
        print(f"Password Length: {len(config.sharepoint.password)}")

        # Получаем connection details из конфигурации
        site_url = config.sharepoint.site_url
        username = config.sharepoint.username
        password = config.sharepoint.password

        # Создаем полный URL для REST API SharePoint
        rest_url = urljoin(site_url, '_api/web')

        print(f"REST API URL: {rest_url}")

        # Создаем контекст аутентификации
        ctx_auth = AuthenticationContext(url=rest_url)

        # Попытка аутентификации
        if ctx_auth.acquire_token_for_user(username, password):
            # Создаем клиентский контекст
            ctx = ClientContext(rest_url, ctx_auth)

            # Проверка подключения
            web = ctx.web
            ctx.load(web)

            try:
                # Выполнение запроса
                ctx.execute_query()
                print("Аутентификация и подключение успешны.")

                # Получаем списки для проверки
                lists = web.lists
                ctx.load(lists)
                ctx.execute_query()

                print("Списки SharePoint успешно загружены.")
                print(f"Количество списков: {len(lists)}")

                logger.info(f"Successfully authenticated to SharePoint site: {site_url}")
                return ctx

            except Exception as execute_error:
                print("Ошибка при выполнении запроса:")
                print(traceback.format_exc())
                raise

        else:
            # Получаем подробности об ошибке аутентификации
            error_details = ctx_auth.get_last_error()
            print("Ошибка аутентификации:")
            print(f"Детали ошибки: {error_details}")
            raise ValueError(f"Authentication failed. Error: {error_details}")

    except Exception as e:
        print("Полная трассировка ошибки:")
        print(traceback.format_exc())
        logger.error(f"SharePoint authentication error: {str(e)}")
        raise

# Дополнительные утилиты для работы с SharePoint
def get_library_items(ctx, library_title):
    """
    Получение элементов из библиотеки SharePoint

    Args:
        ctx (ClientContext): Контекст клиента SharePoint
        library_title (str): Название библиотеки

    Returns:
        List: Список элементов в библиотеке
    """
    try:
        # Получаем список по названию
        library = ctx.web.lists.get_by_title(library_title)

        # Загружаем элементы списка
        items = library.get_items()
        ctx.load(items)
        ctx.execute_query()

        return items

    except Exception as e:
        logger.error(f"Ошибка получения элементов библиотеки {library_title}: {str(e)}")
        raise
