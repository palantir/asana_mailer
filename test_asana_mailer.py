import datetime
import nose
import unittest

import asana_mailer


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
    def setUpClass(cls):
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
    pass


if __name__ == '__main__':
    nose.main()
