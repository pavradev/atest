from enum import Enum
from functools import wraps
import os
import sys
import time
import textwrap
import asyncio
from importlib.util import spec_from_file_location, module_from_spec
import inspect
import traceback
from typing import List, Optional
from datetime import timedelta

if len(sys.argv) != 2:
    print("Error: This script requires one command line argument for tests location.")
    sys.exit(1)

tests_path = sys.argv[1]
print(tests_path)

def get_python_files(path):
    """
    Reads all Python files from the given directory path.
    """
    # List all files in the directory
    file_list = os.listdir(path)
    # Filter the list to only include .py files
    py_files = filter(lambda x: x.endswith('.py'), file_list)
    # Loop through the Python files and yield their paths
    for py_file in py_files:
        yield os.path.join(path, py_file)


def load_script_from_location(location):
    """
    Dynamically loads a Python script from the given location.
    """
    # Create a module name based on the file name
    filename = os.path.basename(location)   
    name_without_extension = os.path.splitext(filename)[0]
    module_name = name_without_extension
    spec = spec_from_file_location(module_name, location)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_function_async(func_name: str, func):
    if not inspect.iscoroutinefunction(func):
        raise ValueError(f"Test function {func_name} is not async")

class TestStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    FAILED = "FAILED"

class TestResult:
    """
    A class representing the result of a test.
    """
    def __init__(self, 
                 exec_time: int, 
                 name: str, 
                 module: str, 
                 status: TestStatus,
                 error: Optional[BaseException] = None):
        self.exec_time = exec_time
        self.module = module
        self.name = name
        self.status = status
        self.error = error


    def __repr__(self):
        return f"TestResult(execution_time={self.exec_time}, name='{self.name}', status={self.status})"


def wrap_test_func(file_location, func_name, test_func):

    @wraps(test_func)
    async def test_func_wrapper(*args, **kwargs):
        start = time.time()
        try:
            await test_func(*args, **kwargs)
            status = TestStatus.SUCCESS
            error = None
        except AssertionError as e:
            status = TestStatus.FAILED
            error = e
        except Exception as e:
            status = TestStatus.ERROR
            error = e
        exec_time = time.time() - start
        return TestResult(
            exec_time=exec_time, 
            module=file_location, 
            name=func_name, 
            status=status,
            error=error)

    return test_func_wrapper

def print_test_results(test_results: List[TestResult]) -> None:
    print(f"{'='*33} TEST RESULTS {'='*33}\n")
    for result in test_results:
        exec_time_formatted = "{:.1f}".format(result.exec_time)
        name = result.name
        module = result.module
        status = result.status.value
        color = "\033[92m" if status == "SUCCESS" else "\033[91m"
        print(f"{module}::{name} {color}{status:<10}\033[0m [{exec_time_formatted}s]")

def print_summary(results: List[TestResult], total_exec_time) -> None:
    """
    Prints a summary of the test results to stdout.

    Args:
        results: List of TestResult objects.
    """
    num_tests = len(results)
    num_passed = sum(1 for r in results if r.status == TestStatus.SUCCESS)
    num_failed = num_tests - num_passed
    total_time_formatted = str(timedelta(seconds=round(total_exec_time)))
    status_line = f"{'='*80}\n"
    if num_failed > 0:
        status_line += f"\033[31m{num_failed} failed\033[0m, "
    status_line += f"\033[32m{num_passed} passed\033[0m in {total_exec_time:.1f}s ({total_time_formatted})\n"
    status_line += f"{'='*80}\n"
    print(textwrap.fill(status_line, width=80))

def print_errors(test_results: List[TestResult]) -> None:
    """
    Print the errors for a list of test results.
    """
    print(f"{'='*35} FAILURES {'='*35}\n")
    for result in test_results:
        if result.status != TestStatus.SUCCESS:
            print(f"{result.module}::{result.name}: {type(result.error).__name__}")
            print(result.error)
            traceback.print_tb(result.error.__traceback__)
            print(f"{'='*80}")


async def run_tests():
    all_test_functions = []
    for file_location in get_python_files(tests_path):
        t_module = load_script_from_location(file_location)
        # Get all functions from the module
        module_functions = inspect.getmembers(t_module, inspect.isfunction)
        # Filter the functions to only include those that start with "test_"
        test_functions = [func for func in module_functions if func[0].startswith("test_")]
        # Call each test function
        for func_name, func in test_functions:
            validate_function_async(func_name, func)
            all_test_functions.append(wrap_test_func(
                file_location=file_location, 
                func_name=func_name, 
                test_func=func
            ))
    start = time.time()
    test_results = await asyncio.gather(*[tf() for tf in all_test_functions])
    exec_time = time.time() - start
    print_test_results(test_results)
    print_errors(test_results)
    print_summary(results=test_results, total_exec_time=exec_time)


asyncio.run(run_tests())