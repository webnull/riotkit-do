#!/usr/bin/env python3

import unittest
from rkd.yaml_context import YamlParser
from rkd.inputoutput import IO, NullSystemIO, BufferedSystemIO
from rkd.exception import DeclarationException, YamlParsingException
from rkd.contract import ExecutionContext
from rkd.test import get_test_declaration


class TestYamlContext(unittest.TestCase):
    def test_parse_imports_successful_case(self):
        factory = YamlParser(NullSystemIO())
        imported = factory.parse_imports(['rkd.standardlib.python.PublishTask'])

        self.assertEqual(':py:publish', imported[0].to_full_name())

    def test_parse_imports_wrong_class_type_but_existing(self):
        def test():
            factory = YamlParser(NullSystemIO())
            factory.parse_imports(['rkd.exception.ContextException'])

        self.assertRaises(DeclarationException, test)

    def test_parse_imports_cannot_import_non_existing_class(self):
        def test():
            factory = YamlParser(NullSystemIO())
            factory.parse_imports(['rkd.standardlib.python.WRONG_NAME'])

        self.assertRaises(YamlParsingException, test)

    def test_parse_tasks_successful_case(self):
        """
        Successful case with description, arguments and bash steps
        """

        input_tasks = {
            ':resistentia': {
                'description': 'Against moving the costs of the crisis to the workers!',
                'arguments': {
                    '--picket': {
                        'help': 'Picket form',
                        'required': False,
                        'action': 'store_true'
                    }
                },
                'steps': [
                    'rm -f /tmp/.test_parse_tasks && echo "Resistentia!" > /tmp/.test_parse_tasks'
                ]
            }
        }

        io = IO()
        factory = YamlParser(io)
        parsed_tasks = factory.parse_tasks(input_tasks, '')

        self.assertEqual(':resistentia', parsed_tasks[0].to_full_name(),
                         msg='Expected that the task name will be present')

        declaration = parsed_tasks[0]
        declaration.get_task_to_execute().execute(ExecutionContext(declaration))

        with open('/tmp/.test_parse_tasks', 'r') as test_helper:
            self.assertIn('Resistentia!', test_helper.read(),
                          msg='Expected that echo contents will be visible')

    def test_parse_tasks_signals_error_instead_of_throwing_exception(self):
        """
        Test that error thrown by executed Python code will
        """

        input_tasks = {
            ':song': {
                'description': 'Bella Ciao is an Italian protest folk song that originated in the hardships of the ' +
                               'mondina women, the paddy field workers in the late 19th century who sang it to ' +
                               'protest against harsh working conditions in the paddy fields of North Italy',
                'steps': [
                    '''#!python
print(syntax-error-here)
                    '''
                ]
            }
        }

        io = BufferedSystemIO()
        factory = YamlParser(io)
        parsed_tasks = factory.parse_tasks(input_tasks, '')

        declaration = parsed_tasks[0]
        task = declaration.get_task_to_execute()
        task._io = io

        result = task.execute(ExecutionContext(declaration))

        self.assertEqual(False, result, msg='Expected that syntax error would result in a failure')
        self.assertIn("NameError: name 'syntax' is not defined", io.get_value(), msg='Error message should be attached')
        self.assertIn('File ":song@step 1", line 1', io.get_value(), msg='Stacktrace should be attached')

    def test_create_bash_callable_successful_case(self):
        """ Bash callable test: Successful case """

        io = BufferedSystemIO()
        factory = YamlParser(io)

        declaration = get_test_declaration()

        execute_callable = factory.create_bash_callable(
            'python --version > /tmp/.test_create_bash_callable_successful_case', 500, ':test', '')
        result = execute_callable(ExecutionContext(declaration), declaration.get_task_to_execute())

        with open('/tmp/.test_create_bash_callable_successful_case', 'r') as test_result:
            self.assertIn("Python", test_result.read())
            self.assertTrue(result, msg='python --version should result with a True')