from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
import config

class ActivationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # We only care about messages
        if not isinstance(event, types.Message):
            return await handler(event, data)

        # If bot is enabled, just continue
        if config.BOT_ENABLED:
            return await handler(event, data)

        # If bot is disabled:
        # 1. Allow developer to still use it (optional but helpful)
        user_id = event.from_user.id if event.from_user else None
        if config.DEVELOPER_ID and str(user_id) == str(config.DEVELOPER_ID):
             return await handler(event, data)

        # 2. For everyone else, say it's off and remove keyboard
        await event.answer(
            "Бот в данный момент не включен.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
