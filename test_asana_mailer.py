import argparse
import codecs
import datetime
import glob
import os
import os.path
import smtplib
import unittest

import dateutil
import mock
import nose
import requests

import asana_mailer

from requests.exceptions import HTTPError


class AsanaAPITestCase(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.api = asana_mailer.AsanaAPI('api_key')

    def test_init(self):
        self.assertEqual(type(self).api.api_key, 'api_key')

    @mock.patch('json.loads')
    @mock.patch('requests.get')
    def test_get(self, mock_get_request, mock_json_loads):
        api = type(self).api
        mock_response = mock_get_request.return_value
        mock_response.status_code = requests.codes.ok
        with self.assertRaises(AttributeError):
            api.get('not_an_endpoint')
        with self.assertRaises(KeyError):
            api.get('project', {'invalid_path_var': 'invalid'})
        auth = ('api_key', '')

        # No Path Vars
        api.get('project')
        mock_get_request.assert_called_once_with('{0}{1}'.format(
            api.asana_api_url, api.project_endpoint), params=None, auth=auth)

        mock_get_request.reset_mock()
        api.get('project', {'project_id': u'123'})
        mock_response.json.assert_called_once_with()

        mock_response.reset_mock()
        api.get('project_tasks', {'project_id': u'123'}, expand='.')
        mock_response.json.assert_called_once_with()

        mock_get_request.reset_mock()
        api.get(
            'project_tasks', {'project_id': u'123'}, expand='.',
            params={'opt_expand': 'name'})
        full_endpoint = api.project_tasks_endpoint.format(
            project_id=u'123')
        mock_get_request.assert_called_once_with(
            '{0}{1}'.format(api.asana_api_url, full_endpoint),
            params={'opt_expand': 'name'}, auth=auth)

        mock_response.reset_mock()
        mock_response.status_code = requests.codes.not_found
        mock_response.content = (
            '{"errors": [{"message": "404 Not Found"}]}'
        )
        mock_response.raise_for_status.side_effect = HTTPError()
        with self.assertRaises(HTTPError):
            api.get('task_stories', {'task_id': u'123'})

        # No content should still throw exception
        mock_response.content = None
        with self.assertRaises(HTTPError):
            api.get('task_stories', {'task_id': u'123'})

        mock_response.raise_for_status.side_effect = None
        mock_json_loads.side_effect = TypeError()
        try:
            api.get('project', {'project_id': u'123'})
        except TypeError:
            self.fail(
                'Asana.get should handle TypeError during JSON Error'
                'Conversion')
        mock_json_loads.side_effect = ValueError()
        try:
            api.get('project', {'project_id': u'123'})
        except ValueError:
            self.fail(
                'Asana.get should handle TypeError during JSON Error'
                'Conversion')

        mock_get_request.assertHasCalls([
            mock.call(url='{}{}'.format(
                type(api).asana_api_url,
                type(api).project_endpoint.format(project_id=u'123')),
                auth=auth),
            mock.call(url='{}{}'.format(
                type(api).asana_api_url,
                type(api).project_tasks_endpoint.format(project_id=u'123')),
                auth=auth),
            mock.call(url='{}{}'.format(
                type(api).asana_api_url,
                type(api).task_stories_endpoint.format(task_id=u'123')),
                auth=auth),
        ])


class ProjectTestCase(unittest.TestCase):

    def setUp(self):
        self.id = u'123'
        self.name = 'Test Project'
        self.description = 'Project Description'
        self.project = asana_mailer.Project(
            self.id, self.name, self.description)

    def test_init(self):
        self.assertEquals(self.project.id, self.id)
        self.assertEquals(self.project.name, self.name)
        self.assertEquals(self.project.description, self.description)
        self.assertEquals(self.project.sections, [])
        self.project = asana_mailer.Project(
            self.id, self.name, self.description, ['123'])
        self.assertEquals(self.project.sections, ['123'])

    @mock.patch('asana_mailer.Project.filter_tasks')
    @mock.patch('asana_mailer.Section.create_sections')
    def test_create_project(self, mock_create_sections, mock_filter_tasks):
        mock_asana = mock.MagicMock()
        current_time_utc = datetime.datetime.now(dateutil.tz.tzutc())
        now = current_time_utc.isoformat()
        project_json = {
            u'name': 'My Project',
            u'notes': 'My Project Description'
        }
        project_tasks_json = [
            {
                'id': u'123', u'name': u'Test Section:',
                u'assignee': None, u'completed': False,
                u'notes': u'test_description', u'due_on': None,
                u'tags': []
            },
            {
                u'id': u'456', u'name': u'More Work',
                u'assignee': None,
                u'completed': False,
                u'notes': u'more_test_description',
                u'due_on': None,
                u'tags': []
            },
        ]
        task_comments_json = (
            (
                {u'text': u'blah', u'type': u'comment'},
                {u'text': u'blah2', u'type': u'not_a_comment'}
            ),
            (
                {u'text': u'blah', u'type': 'comment'},
                {u'text': u'blah3', u'type': 'comment'}
            )
        )
        all_calls = [project_json, project_tasks_json]
        all_calls.extend(task_comments_json)
        mock_asana.get.side_effect = all_calls
        new_section = asana_mailer.Section(u'Test Section:')
        new_tasks = (
            asana_mailer.Task(
                u'Do Work', u'test_user', True,
                dateutil.parser.parse(now), u'test_description',
                dateutil.parser.parse(now),
                [u'Tag #{}'.format(i) for i in xrange(5)], [
                    {u'text': u'blah', u'type': u'comment'},
                    {u'text': u'blah2', u'type': u'not_a_comment'}
                ]
            ),
            asana_mailer.Task(
                u'More Work', None, False, None, u'more_test_description',
                None, [], [
                    {u'text': u'blah', u'type': 'comment'},
                    {u'text': u'blah3', u'type': 'comment'}
                ]
            )
        )
        task_comments = {
            u'123': [
                {u'text': u'blah', u'type': u'comment'},
            ],
            u'456': [
                {u'text': u'blah', u'type': 'comment'},
                {u'text': u'blah3', u'type': 'comment'}
            ]
        }
        new_section.add_tasks(new_tasks)
        new_sections = [new_section]

        mock_create_sections.return_value = new_sections
        # No Filters
        new_project = asana_mailer.Project.create_project(
            mock_asana, u'123', current_time_utc)
        self.assertEquals(new_project.sections, new_sections)
        mock_create_sections.assert_called_once_with(
            project_tasks_json, task_comments)
        mock_filter_tasks.assert_called_once_with(
            current_time_utc, section_filters=None, task_filters=None)

        # Completed Lookback
        mock_create_sections.return_value = new_sections
        mock_asana.get.side_effect = all_calls
        lookback_hours = 10
        new_project = asana_mailer.Project.create_project(
            mock_asana, u'123', current_time_utc,
            completed_lookback_hours=lookback_hours)
        completed_since = (current_time_utc - datetime.timedelta(
            hours=lookback_hours)).replace(microsecond=0).isoformat()
        mock_asana.get.assert_any_call(
            'project_tasks', {'project_id': u'123'}, expand='.',
            params={'completed_since': completed_since})

        # Section Filters
        section_filters = (u'Other Section:',)
        mock_filter_tasks.reset_mock()
        mock_create_sections.reset_mock()
        mock_asana.get.side_effect = all_calls
        new_project = asana_mailer.Project.create_project(
            mock_asana, u'123', current_time_utc,
            section_filters=section_filters)
        self.assertEquals(new_project.sections, new_sections)
        mock_create_sections.assert_called_once_with(
            project_tasks_json, {})
        mock_filter_tasks.assert_called_once_with(
            current_time_utc, section_filters=section_filters,
            task_filters=None)

        # Task Filters
        mock_filter_tasks.reset_mock()
        mock_create_sections.reset_mock()
        mock_asana.get.side_effect = all_calls
        task_filters = [u'Tag #1']
        new_project = asana_mailer.Project.create_project(
            mock_asana, u'123', current_time_utc,
            task_filters=task_filters)
        self.assertEquals(new_project.sections, new_sections)
        mock_create_sections.assert_called_once_with(
            project_tasks_json, {})
        mock_filter_tasks.assert_called_once_with(
            current_time_utc, section_filters=None, task_filters=task_filters)

        all_calls[-1] = (
            {u'text': u'blah', u'type': 'not_a_comment'},
            {u'text': u'blah3', u'type': 'not_a_comment'}
        )

        # Task with no comments
        mock_filter_tasks.reset_mock()
        mock_create_sections.reset_mock()
        mock_asana.get.side_effect = all_calls
        new_project = asana_mailer.Project.create_project(
            mock_asana, u'123', current_time_utc)
        self.assertEquals(new_project.sections, new_sections)
        remove_not_comments = dict(task_comments)
        del remove_not_comments[u'456']
        mock_create_sections.assert_called_once_with(
            project_tasks_json, remove_not_comments)
        mock_filter_tasks.assert_called_once_with(
            current_time_utc, section_filters=None, task_filters=None)

    def test_add_section(self):
        self.project.add_section('test')
        self.assertNotIn('test', self.project.sections)
        new_section = asana_mailer.Section('New Section')
        self.project.add_section(new_section)
        self.assertIn(new_section, self.project.sections)

    def test_add_sections(self):
        sections = [asana_mailer.Section('One'), asana_mailer.Section('Two')]
        self.project.add_sections(sections)
        self.assertEquals(self.project.sections, sections)
        self.project.sections = []
        list_with_non_sections = [1, 2, 3]
        list_with_non_sections.extend(sections)
        self.project.add_sections(list_with_non_sections)
        self.assertEquals(self.project.sections, sections)

    def test_filter_tasks(self):
        current_time_utc = datetime.datetime.now(dateutil.tz.tzutc())
        now = current_time_utc.isoformat()
        no_tasks = asana_mailer.Section('No Tasks')
        section_with_tasks = asana_mailer.Section('Some Tasks')
        incomplete_task_with_tags = asana_mailer.Task(
            u'Do Work With Tags', u'test_user', False,
            dateutil.parser.parse(now), u'test_description',
            dateutil.parser.parse(now),
            [u'Tag #{}'.format(i) for i in xrange(5)], [
                {u'text': u'blah', u'type': u'comment'},
                {u'text': u'blah2', u'type': u'not_a_comment'}
            ]
        )
        incomplete_task = asana_mailer.Task(
            u'More Work', None, False, None, u'more_test_description',
            None, [], [
                {u'text': u'blah', u'type': 'comment'},
                {u'text': u'blah3', u'type': 'comment'}
            ]
        )

        section_with_tasks.add_task(incomplete_task)
        self.project.sections = [no_tasks, section_with_tasks]
        self.project.filter_tasks(current_time_utc)
        self.assertEquals(len(self.project.sections), 1)
        self.assertEquals(len(self.project.sections[0].tasks), 1)

        # Section Filters
        section_filters = ('None of these tasks:',)
        self.project.filter_tasks(
            current_time_utc, section_filters=section_filters)
        self.assertEquals(len(self.project.sections), 0)

        # Task Filters
        task_filters = frozenset((u'Tag #1',))
        section_with_tasks.add_task(incomplete_task_with_tags)
        self.project.sections = [no_tasks, section_with_tasks]
        self.project.filter_tasks(current_time_utc, task_filters=task_filters)
        self.assertEquals(len(self.project.sections), 1)
        self.assertEquals(len(self.project.sections[0].tasks), 1)


class SectionTestCase(unittest.TestCase):

    def setUp(self):
        self.section = asana_mailer.Section('Test Section')

    @classmethod
    def setup_class(cls):
        cls.tasks = [
            asana_mailer.Task(
                'Task #{}'.format(i), 'test_assignee', False, None,
                'test_description', None, [], [])
            for i in xrange(5)]

    def test_init(self):
        self.assertEqual(self.section.name, 'Test Section')
        self.assertEqual(self.section.tasks, [])
        self.section = asana_mailer.Section('Test Section', [1, 2, 3])
        self.assertEqual(self.section.name, 'Test Section')
        self.assertEqual(self.section.tasks, [1, 2, 3])

    def test_create_sections(self):
        now = datetime.datetime.now().isoformat()
        project_tasks_json = [
            {
                'id': u'123', u'name': u'Test Section:',
                u'assignee': None, u'completed': False,
                u'notes': 'test_description', u'due_on': None,
                u'tags': []
            },
            {
                u'id': u'321', u'name': u'Do Work',
                u'assignee': {'name': 'test_user'},
                u'completed': True,
                u'completed_at': now,
                u'notes': u'test_description',
                u'due_on': now,
                u'tags': [{u'name': u'Tag #{}'.format(i)} for i in xrange(5)]
            },
            {
                u'id': u'456', u'name': u'More Work',
                u'assignee': None,
                u'completed': False,
                u'notes': u'more_test_description',
                u'due_on': None,
                u'tags': []
            },
        ]
        task_comments = {
            u'123': [
                {u'text': u'blah', u'type': u'comment'},
                {u'text': u'blah2', u'type': u'comment'}
            ],
            u'321': [
                {u'text': u'blah', u'type': 'comment'},
                {u'text': u'blah3', u'type': 'comment'}
            ]
        }
        sections = asana_mailer.Section.create_sections(
            project_tasks_json, task_comments)
        self.assertEquals(len(sections), 1)
        self.assertEquals(sections[0].name, u'Test Section:')
        self.assertEquals(len(sections[0].tasks), 2)
        first_task = sections[0].tasks[0]
        self.assertEquals(first_task.name, u'Do Work')
        self.assertEquals(first_task.assignee, u'test_user')
        self.assertEquals(first_task.completed, True)
        self.assertEquals(
            first_task.completion_time, dateutil.parser.parse(now))
        self.assertEquals(first_task.description, u'test_description')
        self.assertEquals(first_task.due_date, now)
        self.assertEquals(first_task.comments, [
            {u'text': u'blah', u'type': 'comment'},
            {u'text': u'blah3', u'type': 'comment'}
        ])
        self.assertEquals(
            first_task.tags, [u'Tag #{}'.format(i) for i in xrange(5)])
        second_task = sections[0].tasks[1]
        self.assertIsNone(second_task.assignee)
        self.assertEquals(second_task.name, u'More Work')
        self.assertFalse(second_task.completed)
        self.assertIsNone(second_task.completion_time)
        self.assertEquals(second_task.description, u'more_test_description')
        self.assertIsNone(second_task.due_date)
        self.assertEquals(second_task.tags, [])

        project_tasks_json.append(
            {u'id': u'654', u'name': u'Section With No Tasks:'})
        sections = asana_mailer.Section.create_sections(
            project_tasks_json, task_comments)
        self.assertEquals(len(sections), 1)
        self.assertEquals(len(sections[0].tasks), 2)

        project_tasks_json.insert(
            0,
            {
                u'id': u'789', u'name': u'Misc Task', u'assignee': None,
                u'completed': False, u'notes': None, u'due_on': None,
                u'tags': []
            }
        )
        sections = asana_mailer.Section.create_sections(
            project_tasks_json, task_comments)
        print [s.name for s in sections]
        self.assertEquals(len(sections), 2)
        self.assertEquals(sections[-1].name, u'Misc:')
        self.assertEquals(len(sections[-1].tasks), 1)
        misc_task = sections[-1].tasks[0]
        self.assertEquals(misc_task.name, u'Misc Task')
        self.assertIsNone(misc_task.assignee)
        self.assertFalse(misc_task.completed)
        self.assertIsNone(misc_task.description)
        self.assertIsNone(misc_task.due_date)
        self.assertEquals(misc_task.tags, [])

    def test_add_task(self):
        self.section.add_task('test')
        self.assertNotIn('test', self.section.tasks)
        self.section.add_task(type(self).tasks[0])
        self.assertIn(type(self).tasks[0], self.section.tasks)

    def test_add_tasks(self):
        self.section.add_tasks(type(self).tasks)
        self.assertEquals(type(self).tasks, self.section.tasks)
        self.section.tasks = []
        list_with_non_tasks = [1, 2, 3]
        list_with_non_tasks.extend(type(self).tasks)
        self.section.add_tasks(list_with_non_tasks)
        self.assertEquals(type(self).tasks, self.section.tasks)


class FiltersTestCase(unittest.TestCase):

    def test_last_comment(self):
        self.assertEqual(asana_mailer.last_comment([]), [])
        self.assertEqual(asana_mailer.last_comment(None), [])
        self.assertEqual(asana_mailer.last_comment([1, 2, 3]), [3])
        self.assertEqual(asana_mailer.last_comment([1, 3]), [3])
        self.assertEqual(asana_mailer.last_comment([1]), [1])

    def test_most_recent_comments(self):
        comments = [1, 2, 3]
        self.assertEqual(asana_mailer.most_recent_comments(comments, 0), [3])
        self.assertEqual(
            asana_mailer.most_recent_comments(comments, 4), [1, 2, 3])

        self.assertEqual(asana_mailer.most_recent_comments(comments, 1), [3])
        self.assertEqual(
            asana_mailer.most_recent_comments(comments, 2), [2, 3])
        self.assertEqual(
            asana_mailer.most_recent_comments(comments, 3), [1, 2, 3])

        self.assertEqual(asana_mailer.most_recent_comments([], 5), [])
        self.assertEqual(asana_mailer.most_recent_comments([], 1), [])

    def test_comments_within_lookback(self):
        now = datetime.datetime.now(dateutil.tz.tzutc())
        comments = [
            {u'created_at': (now - datetime.timedelta(days=i)).isoformat()}
            for i in reversed(xrange(7))
        ]
        self.assertEqual(
            asana_mailer.comments_within_lookback(comments, now, 0),
            comments[-1:])
        self.assertEqual(
            asana_mailer.comments_within_lookback(comments, now, 24),
            comments[-1:])
        self.assertEqual(
            asana_mailer.comments_within_lookback(comments, now, 25),
            comments[-2:])
        self.assertEqual(
            asana_mailer.comments_within_lookback(comments, now, 49),
            comments[-3:])
        print comments
        self.assertEqual(
            asana_mailer.comments_within_lookback(comments, now, 144),
            comments[1:])
        self.assertEqual(
            asana_mailer.comments_within_lookback(comments, now, 200),
            comments)
        self.assertEqual(
            asana_mailer.comments_within_lookback([], now, 200), [])

    def test_as_date(self):
        now = datetime.datetime.now()
        now_str = now.isoformat()
        now_date_str = now.date().isoformat()
        self.assertEqual(asana_mailer.as_date('garbage'), 'garbage')
        self.assertEqual(asana_mailer.as_date(now_str), now_date_str)


class TaskTestCase(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        now = datetime.datetime.now(dateutil.tz.tzutc())
        name = 'Test'
        assignee = 'TestUser'
        completed = True
        completion_time = now
        description = 'A test!'
        due_date = now.date().isoformat()
        tags = ['test1', 'test2']
        comments = []
        cls.task = asana_mailer.Task(
            name, assignee, completed, completion_time, description, due_date,
            tags, comments)

    def test_init(self):
        original = type(self).task
        task = asana_mailer.Task(
            original.name, original.assignee,
            original.completed, original.completion_time,
            original.description, original.due_date,
            original.tags, original.comments)
        self.assertEqual(task.name, original.name)
        self.assertEqual(task.assignee, original.assignee)
        self.assertEqual(task.completed, original.completed)
        self.assertEqual(task.completion_time, original.completion_time)
        self.assertEqual(task.description, original.description)
        self.assertEqual(task.due_date, original.due_date)
        self.assertEqual(task.tags, original.tags)
        self.assertEqual(task.comments, original.comments)

    def test_tags_in(self):
        filter_set = set()
        self.assertEqual(type(self).task.tags_in(filter_set), True)
        filter_set = {'test1'}
        self.assertEqual(type(self).task.tags_in(filter_set), True)
        filter_set = {'test1', 'test2'}
        self.assertEqual(type(self).task.tags_in(filter_set), True)
        filter_set = {'test1', 'test2', 'test3'}
        self.assertEqual(type(self).task.tags_in(filter_set), False)


class AsanaMailerTestCase(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.current_time_utc = datetime.datetime.now(dateutil.tz.tzutc())
        cls.current_date = datetime.date.today()

    @classmethod
    def teardown_class(cls):
        for fname in glob.glob('AsanaMailer_*.*'):
            if os.path.exists(fname):
                os.remove(fname)

    @mock.patch('premailer.transform')
    @mock.patch('asana_mailer.FileSystemLoader')
    @mock.patch('asana_mailer.Environment')
    def test_generate_templates(
            self, mock_jinja_env, mock_fs_loader, mock_transform):
        mock_fs_instance = mock_fs_loader.return_value
        mock_env_instance = mock_jinja_env.return_value
        mock_get_template = mock_env_instance.get_template.return_value
        mock_get_template.render.return_value = 'template render'
        mock_transform.return_value = 'premailer transform'

        project = mock.MagicMock()

        return_vals = asana_mailer.generate_templates(
            project, 'html_template', 'text_template', type(self).current_date,
            type(self).current_time_utc)
        mock_jinja_env.assert_called_once_with(
            loader=mock_fs_instance, trim_blocks=True, lstrip_blocks=True,
            autoescape=True)

        mock_env_instance.get_template.assert_has_calls(
            [mock.call('html_template'), mock.call('text_template')],
            any_order=True)
        mock_fs_loader.assert_called_once_with('templates')
        self.assertFalse(mock_env_instance.autoescape)

        self.assertEquals(
            ('premailer transform', 'template render'), return_vals)

    @mock.patch('datetime.date')
    @mock.patch('datetime.datetime')
    @mock.patch('asana_mailer.write_rendered_files')
    @mock.patch('asana_mailer.send_email')
    @mock.patch('asana_mailer.generate_templates')
    @mock.patch('asana_mailer.Project.create_project')
    @mock.patch('asana_mailer.AsanaAPI')
    @mock.patch('asana_mailer.create_cli_parser')
    def test_main(
            self, mock_cli_parser, mock_asana_api, mock_create_project,
            mock_generate_templates, mock_send_email,
            mock_write_rendered_files, mock_datetime, mock_date):

        mock_cli_instance = mock_cli_parser.return_value
        mock_cli_instance.error.side_effect = SystemExit(2)
        mock_create_project.return_value = 'Project'
        mock_asana_instance = mock_asana_api.return_value
        mock_datetime_now_instance = mock_datetime.now.return_value
        mock_date.today.return_value = 'Mock Date'
        mock_generate_templates.return_value = (
            'rendered_html', 'rendered_text')

        # Specify an to/from address(es), but not both
        mock_cli_instance.parse_args.return_value = argparse.Namespace(
            from_address=None, to_addresses=['example@example.com'])
        with self.assertRaises(SystemExit) as cm:
            asana_mailer.main()
        self.assertEquals(cm.exception.code, 2)

        namespace = argparse.Namespace(
            api_key='api_key',
            tag_filters=['tag_filter'],
            section_filters=['section_filter'],
            project_id='project_id',
            completed_lookback_hours=None,
            html_template='Mock.html',
            text_template='Mock.markdown',
            mail_server='mockhost',
            cc_addresses=None,
            from_address='example@example.com',
            to_addresses=['example2@example.com'])
        mock_cli_instance.parse_args.return_value = namespace
        asana_mailer.main()
        mock_asana_api.assert_called_once_with('api_key')
        mock_create_project.assert_called_once_with(
            mock_asana_instance, 'project_id', mock_datetime_now_instance,
            task_filters=frozenset((u'tag_filter',)),
            section_filters=frozenset((u'section_filter:',)),
            completed_lookback_hours=None)
        mock_generate_templates.assert_called_once_with(
            'Project', 'Mock.html', 'Mock.markdown', 'Mock Date',
            mock_datetime_now_instance)
        mock_send_email.assert_called_once_with(
            'Project', 'mockhost', 'example@example.com',
            ['example2@example.com'], None, 'rendered_html', 'rendered_text',
            'Mock Date')

        # With Cc Addresses
        namespace.cc_addresses = [
            'example3@example.com', 'example4@example.com'
        ]
        mock_cli_instance.parse_args.return_value = namespace
        mock_send_email.reset_mock()
        asana_mailer.main()
        mock_send_email.assert_called_once_with(
            'Project', 'mockhost', 'example@example.com',
            ['example2@example.com'],
            ['example3@example.com', 'example4@example.com'], 'rendered_html',
            'rendered_text', 'Mock Date')

        # With No Addresses
        namespace.to_addresses = None
        namespace.from_address = None
        mock_cli_instance.parse_args.return_value = namespace
        mock_send_email.reset_mock()
        asana_mailer.main()
        self.assertEquals(mock_send_email.call_count, 0)
        mock_write_rendered_files.assert_called_once_with(
            'rendered_html', 'rendered_text', 'Mock Date')

    @mock.patch('asana_mailer.MIMEText')
    @mock.patch('asana_mailer.MIMEMultipart')
    @mock.patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp, mock_mime_multipart, mock_mime_text):
        project = mock.MagicMock()
        project.name = 'Test Project'
        from_address = 'test@example.com'
        to_addresses = ['test2@example.com', 'test3@example.com']
        cc_addresses = ['test4@example.com', 'test5@example.com']
        combined_addresses = to_addresses + cc_addresses

        smtp_mock_instance = mock_smtp.return_value
        multipart_mock_instance = mock_mime_multipart.return_value
        text_mock_instance = mock_mime_text.return_value

        msg_dict = {}

        def get_item(key):
            return msg_dict[key]

        def set_item(key, val):
            msg_dict[key] = val

        multipart_mock_instance.__getitem__.side_effect = get_item
        multipart_mock_instance.__setitem__.side_effect = set_item
        multipart_mock_instance.as_string.return_value = 'test message'

        asana_mailer.send_email(
            project, 'localhost', from_address, to_addresses[:],
            cc_addresses[:], 'test_html', 'test_text', type(self).current_date)

        mock_mime_multipart.assert_called_with('alternative')
        self.assertEquals(
            multipart_mock_instance['Subject'], '{0} Daily Mailer {1}'.format(
                project.name, type(self).current_date))
        self.assertEquals(multipart_mock_instance['From'], from_address)
        self.assertEquals(
            multipart_mock_instance['To'], ', '.join(to_addresses))
        self.assertEquals(
            multipart_mock_instance['Cc'], ', '.join(cc_addresses))

        text_calls = [
            mock.call('test_text'.encode('utf-8'), 'plain'),
            mock.call('test_html'.encode('utf-8'), 'html')
        ]
        mock_mime_text.assert_has_calls(text_calls)
        self.assertEquals(mock_mime_text.call_count, 2)
        multipart_mock_instance.attach.assert_has_calls(
            [mock.call(text_mock_instance), mock.call(text_mock_instance)],
            any_order=True)
        self.assertEquals(multipart_mock_instance.attach.call_count, 2)

        mock_smtp.assert_called_with('localhost', timeout=300)
        smtp_mock_instance.sendmail.assert_called_once_with(
            from_address, combined_addresses, 'test message'
        )
        smtp_mock_instance.quit.assert_called_once_with()

        # No Cc Addresses
        smtp_mock_instance.sendmail.reset_mock()
        smtp_mock_instance.quit.reset_mock()
        asana_mailer.send_email(
            project, 'localhost', from_address, to_addresses[:], None,
            'test_html', 'test_text', type(self).current_date)

        self.assertEquals(
            multipart_mock_instance['To'], ', '.join(to_addresses))
        self.assertNotIn('Cc', multipart_mock_instance)
        smtp_mock_instance.sendmail.assert_called_once_with(
            from_address, to_addresses, 'test message'
        )
        smtp_mock_instance.quit.assert_called_once_with()

        smtp_mock_instance.sendmail.side_effect = smtplib.SMTPException
        try:
            asana_mailer.send_email(
                project, 'localhost', from_address, to_addresses[:], None,
                'test_html', 'test_text', type(self).current_date)
        except smtplib.SMTPException:
            self.fail('asana_mailer.send_email threw an SMTPException!')

    def test_write_rendered_files(self):
        today = type(self).current_date.isoformat()
        filenames = (
            'AsanaMailer_{0}.html'.format(today),
            'AsanaMailer_{0}.markdown'.format(today))
        asana_mailer.write_rendered_files('testing', 'testing', today)
        for fname in filenames:
            self.assertTrue(os.path.exists(fname))
            with codecs.open(fname, 'r', 'utf-8') as fobj:
                self.assertEqual(fobj.read(), 'testing')


if __name__ == '__main__':
    nose.main()
