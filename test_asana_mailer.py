import codecs
import datetime
import glob
import os
import os.path
import unittest

import dateutil
import mock
import nose

import asana_mailer


class AsanaAPITestCase(unittest.TestCase):
    pass


class ProjectTestCase(unittest.TestCase):
    pass


class SectionTestCase(unittest.TestCase):
    pass


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
        now = datetime.datetime.utcnow()
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
        now = datetime.datetime.utcnow()
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

    def test_incomplete_or_recent(self):
        original = type(self).task
        now = datetime.datetime.utcnow()
        task = asana_mailer.Task(
            original.name, original.assignee,
            original.completed, original.completion_time,
            original.description, original.due_date,
            original.tags, original.comments)

        task.completed = True
        task.completion_time = now
        self.assertEqual(task.incomplete_or_recent(now, 0), False)
        self.assertEqual(task.incomplete_or_recent(now, 1), True)
        task.completion_time = now - datetime.timedelta(days=2)
        self.assertEqual(task.incomplete_or_recent(now, 1), False)
        self.assertEqual(task.incomplete_or_recent(now, 48), False)
        self.assertEqual(task.incomplete_or_recent(now, 49), True)

        task.completed = False
        self.assertEqual(task.incomplete_or_recent(now, 0), True)

    def test_incomplete_or_recent_json(self):
        now = datetime.datetime.utcnow()
        tasks = [
            {u'completed_at': (now - datetime.timedelta(days=i)).isoformat()}
            for i in reversed(xrange(2))
        ]
        for t in tasks:
            t[u'completed'] = True

        self.assertEqual(
            asana_mailer.Task.incomplete_or_recent_json(now, tasks[-1], 0),
            False)
        self.assertEqual(
            asana_mailer.Task.incomplete_or_recent_json(now, tasks[-1], 1),
            True)
        self.assertEqual(
            asana_mailer.Task.incomplete_or_recent_json(now, tasks[-2], 24),
            False)
        self.assertEqual(
            asana_mailer.Task.incomplete_or_recent_json(now, tasks[-2], 25),
            True)

        incomplete = {u'completed_at': now.isoformat(), u'completed': False}
        self.assertEqual(
            asana_mailer.Task.incomplete_or_recent_json(now, incomplete, 0),
            True)

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
