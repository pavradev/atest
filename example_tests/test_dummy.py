import asyncio

async def util_function():
    print("util")

async def test_http_call_1():
    print("start 1")
    await asyncio.sleep(1)
    print("end 1")

async def test_http_call_2():
    print("start 2")
    await asyncio.sleep(1)
    x = []
    print(x.length)

async def test_http_call_3():
    print("start 3")
    await asyncio.sleep(1)
    assert False

async def test_http_call_4():
    print("start 4")
    await asyncio.sleep(1)
    print("end 4")

async def test_http_call_5():
    print("start 5")
    await asyncio.sleep(1)
    print("end 5")