from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Awaitable, Optional
import asyncio

from llm.cloud import ChainPart1UserInput, CloudLLMCache, DailyPlanner
from llm.local import LocalLLMCache, LocalLLMInput, LocalPlanner

class BaseLLMManager(ABC):
    
    refresh_interval: timedelta
    is_running: bool
    _task: Optional[asyncio.Task] = None
    _stop_event: asyncio.Event
    _manual_refresh_event: asyncio.Event

    def __init__(self, refresh_interval: timedelta) -> None:
        self.refresh_interval = refresh_interval
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._manual_refresh_event = asyncio.Event()

    def start(self, *args, **kwargs) -> None:
        if not self.is_running:
            self.is_running = True
            self._stop_event.clear()
            self._manual_refresh_event.clear()
            self._task = asyncio.create_task(self._run(*args, **kwargs))
        else:
            print(f"[{self.__class__.__name__}] Already running.")

    async def stop(self) -> None:
        if self.is_running:
            self.is_running = False
            self._stop_event.set()
            if self._task:
                await self._task
                self._task = None
        else:
            print(f"[{self.__class__.__name__}] Not running.")


    @abstractmethod
    async def generate_plan(self, *args, **kwargs) -> object:
        pass

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                try:
                    await self.generate_plan()
                    await asyncio.wait_for(
                        self._manual_refresh_event.wait(),
                        timeout=self.refresh_interval.total_seconds()
                    )
                except asyncio.TimeoutError:
                    pass
                self._manual_refresh_event.clear()
            except Exception as e:
                print(f"[{self.__class__.__name__}] Error during refresh: {e}")


    async def manual_refresh(self) -> None:
        """
        Manually trigger a refresh of the LLM cache and planner.
        """
        if self.is_running:
            await self.generate_plan()
            self._manual_refresh_event.set()
        else:
            print(f"[{self.__class__.__name__}] Cannot refresh, not running.")



class CloudLLMManager(BaseLLMManager):
    cache: CloudLLMCache
    planner: DailyPlanner
    _user_input: Optional[ChainPart1UserInput] = None
    _demo: bool = True
    def __init__(self, openai_key: str, preplexity_key: str, refresh_interval: timedelta, demo: bool = True) -> None:
        super().__init__(refresh_interval)
        self.cache = CloudLLMCache()
        self.planner = DailyPlanner(openai_key, preplexity_key)
        self._demo = demo

    def set_user_input(self, user_input: ChainPart1UserInput) -> None:
        """
        Set the user input for the LLM manager.
        """
        self._user_input = user_input

    async def generate_plan(self) -> object:
        if self._user_input:
            await self.cache.refresh_plan(self.planner, self._user_input, self._demo)

class LocalLLMManager(BaseLLMManager):
    cache: LocalLLMCache
    planner: LocalPlanner
    current_input: Optional[LocalLLMInput] = None
    def __init__(self, refresh_interval: timedelta, planner: LocalPlanner) -> None:
        super().__init__(refresh_interval)
        self.cache = LocalLLMCache.get_instance()
        self.planner = planner

    def set_user_input(self, user_input: LocalLLMInput) -> None:
        """
        Set the user input for the local LLM manager.
        """
        self.current_input = user_input

    async def generate_plan(self) -> object:
        if self.current_input:
            await self.cache.refresh_plan(self.current_input)
        else:
            raise ValueError("User input must be set before generating a plan.")
    


