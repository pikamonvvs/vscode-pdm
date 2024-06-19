import asyncio

import aioconsole


class AsyncTaskManager:
    def __init__(self):
        self.tasks = {}
        self.count = 0

    async def execute(self, task_id, duration, interval):
        print(f"Task #{task_id} started. (duration: {duration}s)")
        try:
            while duration > 0:
                duration -= 1
                print(f"Task #{task_id} running...")
                await asyncio.sleep(interval)
            print(f"Task #{task_id} ended.")
        except asyncio.CancelledError:
            print(f"Task #{task_id} was cancelled.")

    def register_task(self, duration, interval):
        self.count += 1
        id = self.count
        task = asyncio.create_task(self.execute(id, duration, interval))
        self.tasks[id] = task
        print(f"Task #{id} registered.")
        return id

    def deregister_task(self, task_id):
        task = self.tasks.pop(task_id, None)
        if task:
            task.cancel()
            print(f"Task #{task_id} deregistered.")
        else:
            print(f"Task #{task_id} not found.")


async def main():
    manager = AsyncTaskManager()

    while True:
        switch = await aioconsole.ainput(
            "Enter 1 to register a task, 0 to deregister a task, or any other key to exit: "
        )
        if switch == "1":
            duration = await aioconsole.ainput("Enter the duration of the task in seconds: ")
            interval = await aioconsole.ainput("Enter the interval of the task in seconds: ")
            manager.register_task(int(duration), float(interval))
        elif switch == "0":
            task_id = await aioconsole.ainput("Enter the ID of the task to deregister: ")
            manager.deregister_task(int(task_id))
        else:
            break

    # Wait for all tasks to complete
    await asyncio.gather(*manager.tasks.values(), return_exceptions=True)


# Run the main coroutine
asyncio.run(main())
