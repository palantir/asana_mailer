#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2013 Palantir Technologies

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Asana Mailer is a script that retrieves metadata from an Asana project via
Asana's REST API to generate a plaintext and HTML email using Jinja2 templates.

:copyright: (c) 2013 by Palantir Technologies
:license: Apache 2.0, see LICENSE for more details.
'''

import argparse
import codecs
import datetime
import dateutil.parser
import dateutil.tz
import premailer
import requests
import smtplib
import sys

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader


class Asana(object):
    '''The class for making calls to Asana's REST API.

    The Asana class represents the infrastructure for storing a user's API key
    and making calls to Asana's API. It is utilized for generating the Project
    and its contained objects (Section, Task, etc.).
    '''

    asana_api_url = 'https://app.asana.com/api/1.0/'
    project_endpoint = 'projects/{project_id}'
    project_tasks_endpoint = 'projects/{project_id}/tasks?opt_expand=.'
    task_stories_endpoint = 'tasks/{task_id}/stories'

    def __init__(self, api_key):
        self.api_key = api_key

    def api_call(self, endpoint_name, **kwargs):
        '''Makes a call to Asana's API.

        :param endpoint_name: The endpoint attribute to connect to
        :param **kwargs: The keyword arguments necessary for retrieving data
        from a particular endpoint
        '''
        endpoint = getattr(
            self.__class__, '{0}_endpoint'.format(endpoint_name))
        url = '{0}{1}'.format(
            self.__class__.asana_api_url, endpoint.format(**kwargs))
        response = requests.get(url, auth=(self.api_key, ''))
        if response.status_code == requests.codes.ok:
            return response.json()['data']


class Project(object):
    '''An object that represents an Asana Project and its metadata.

    It is intended to be created via its create_project method, which utilizes
    an Asana object to make calls to Asana's API. It also handles creating
    sections and their associated task objects, as well as filtering tasks and
    sections.
    '''

    def __init__(self, name, description, sections=None):
        self.name = name
        self.description = description
        self.sections = sections
        if self.sections is None:
            self.sections = []

    @staticmethod
    def create_project(
            asana, project_id, filters=None, section_filters=None,
            keep_completed=False):
        '''Creates a Project utilizing data from Asana.

        Using filters, a project attempts to optimize the calls it makes to
        Asana's API. After the JSON data has been collected, it is then parsed
        into Task and Section objects, and then filtered again in order to
        perform filtering that is only possible post-parsing.

        :param asana: The initialized Asana object that makes API calls
        :param project_id: The Asana Project ID
        :param filters: A list of tag filters for filtering out tasks
        :param section_filters: A list of sections to filter out tasks
        :param keep_completed: A boolean representing whether to store
        recently completed tasks
        :return: The newly created Project instance
        '''
        current_time_utc = datetime.datetime.now(dateutil.tz.tzutc())
        project_json = asana.api_call('project', project_id=project_id)
        project_tasks_json = asana.api_call(
            'project_tasks', project_id=project_id)
        task_last_comments = {}

        current_section = None
        for task in project_tasks_json:
            if task['name'].endswith(':'):
                current_section = task['name']
            if section_filters and current_section not in section_filters:
                continue
            tag_names = frozenset((tag['name'] for tag in task['tags']))
            # Optimize calls to API
            if filters and not tag_names >= filters:
                continue
            elif keep_completed and not Task.incomplete_or_recent_json(
                    current_time_utc, task):
                continue
            elif not keep_completed and task['completed']:
                continue
            task_id = unicode(task['id'])
            task_stories = asana.api_call('task_stories', task_id=task_id)
            task_comments = [
                story for story in task_stories if
                story['type'] == 'comment']
            if task_comments:
                task_last_comments[task_id] = task_comments[-1]

        project = Project(project_json['name'], project_json['notes'])
        project.add_sections(
            Section.create_sections(project_tasks_json, task_last_comments))
        project.filter_sections(section_filters)
        project.filter_tasks(filters)
        project.remove_completed_tasks(keep_completed, current_time_utc)

        return project

    def add_section(self, section):
        '''Add a section to the project.

        :param section: The section to add to the project
        '''
        self.sections.append(section)

    def add_sections(self, sections):
        '''Add multiple sections to the project.

        :param sections: A list of sections to add to the project
        '''
        self.sections.extend(sections)

    def filter_sections(self, sections_filters):
        '''Filter out sections based on a list of filter criteria.

        :param sections_filters: A list of sections to filter the Project on
        '''
        if sections_filters:
            self.sections[:] = [
                s for s in self.sections if s.name in sections_filters]

    def filter_tasks(self, filters):
        '''Filter out tasks based on a list of filter criteria.

        :param filters: A list of tags to filter the Project's tasks on
        '''
        if filters:
            for section in self.sections:
                section.tasks[:] = [
                    task for task in section.tasks if task.tags_in(filters)]
            self.sections[:] = [s for s in self.sections if s.tasks]

    def remove_completed_tasks(self, keep_completed, current_time_utc=None):
        '''Remove completed tasks, or tasks completed within 36 hours.

        :param keep_completed: A boolean representing how to remove completed
        tasks. If False, all completed tasks are filtered out. If True, then
        recently completed tasks (currently 36 hours) are kept.
        :param current_time_utc: The current time in UTC that is passed in
        '''
        for section in self.sections:
            if keep_completed:
                section.tasks = [task for task in section.tasks if (
                    task.incomplete_or_recent(current_time_utc))]
            else:
                section.tasks[:] = [
                    task for task in section.tasks if not task.completed]


class Section(object):
    '''A class representing a section of tasks within an Asana Project.'''

    def __init__(self, name, tasks=None):
        self.name = name
        self.tasks = tasks
        if self.tasks is None:
            self.tasks = []

    @staticmethod
    def create_sections(project_tasks_json, task_last_comments):
        '''Creates sections from task and story JSON from Asana's API.

        :param project_tasks_json: The JSON object for a Project's tasks in
        Asana
        :param task_last_comments: The last comments (stories) for all of the
        tasks in the tasks JSON
        '''
        sections = []
        misc_section = Section(u'Misc')
        current_section = misc_section
        for task in project_tasks_json:
            if task['name'].endswith(':'):
                if current_section.tasks and current_section.name != u'Misc':
                    sections.append(current_section)
                current_section = Section(task['name'])
            else:
                name = task['name']
                if task['assignee']:
                    assignee = task['assignee']['name']
                else:
                    assignee = None
                task_id = unicode(task['id'])
                completed = task['completed']
                if completed:
                    completion_time = dateutil.parser.parse(
                        task['completed_at'])
                else:
                    completion_time = None
                description = task['notes'] if task['notes'] else None
                due_date = task['due_on']
                tags = [tag['name'] for tag in task['tags']]
                latest_comment = task_last_comments.get(task_id)
                current_task = Task(
                    name, assignee, completed, completion_time, description,
                    due_date, tags, latest_comment)
                current_section.add_task(current_task)
        if current_section.tasks:
            sections.append(current_section)
        if misc_section.tasks and current_section != misc_section:
            sections.append(misc_section)
        return sections

    def add_task(self, task):
        '''Add a task to a Section's list of tasks.

        :param task: The task to add to the Section's list of tasks
        '''
        self.tasks.append(task)

    def add_tasks(self, tasks):
        '''Extend the Section's list of tasks with a new list of tasks.

        :param tasks: The list of tasks to extend the Section's list of tasks.
        '''
        self.tasks.extend(tasks)


class Task(object):
    '''A class representing an Asana Task.'''

    def __init__(
            self, name, assignee, completed, completion_time, description,
            due_date, tags, latest_comment):
        self.name = name
        self.assignee = assignee
        self.completed = completed
        self.completion_time = completion_time
        self.description = description
        self.due_date = due_date
        self.tags = tags
        self.latest_comment = latest_comment

    @staticmethod
    def incomplete_or_recent_json(current_time_utc, task_json):
        '''Returns whether a task's JSON is incomplete or recently completed.

        :param current_time_utc: The current time in UTC
        :param task_json: The JSON representing an Asana task from Asana's API
        '''
        if task_json['completed']:
            task_completion_time = dateutil.parser.parse(
                task_json['completed_at'])
            delta = current_time_utc - task_completion_time
            return delta < datetime.timedelta(hours=36)
        else:
            return True

    def tags_in(self, tag_filter_set):
        '''Determines if a Tasks's tags are within a set of tag filters'''
        task_tag_set = frozenset(self.tags)
        return task_tag_set >= tag_filter_set

    def incomplete_or_recent(self, current_time_utc):
        '''Returns whether a task's is incomplete or recently completed.

        :param current_time_utc: The current time in UTC
        '''
        if self.completed:
            delta = current_time_utc - self.completion_time
            return delta < datetime.timedelta(hours=36)
        else:
            return True


def generate_templates(project, html_template, text_template, current_date):
    '''Generates the templates using Jinja2 templates

    :param html_template: The filename of the HTML template in the templates
    folder
    :param text_template: The filename of the text template in the templates
    folder
    :param current_date: The current date.
    '''
    env = Environment(
        loader=FileSystemLoader('templates'), trim_blocks=True,
        lstrip_blocks=True, autoescape=True)

    html = env.get_template(html_template)
    rendered_html = premailer.transform(
        html.render(project=project, current_date=current_date))

    env.autoescape = False
    plaintext = env.get_template(text_template)
    rendered_plaintext = plaintext.render(project=project)

    return (rendered_html, rendered_plaintext)


def send_email(
        project, from_address, to_addresses, cc_addresses,
        rendered_html, rendered_text, current_date):
    '''Sends an email using a Project and rendered templates.

    :param: The Project instance for this email
    :param from_address: The From: Address for the email to send
    :param to_addresses: The list of To: addresses for the email to be sent to
    :param cc_addresses: The list of Cc: addresses for the email to be sent to
    :param rendered_html: The rendered HTML template
    :param rendered_text: The rendered text template
    :param current_date: The current date
    '''
    message = MIMEMultipart('alternative')
    message['Subject'] = '{0} Daily Mailer {1}'.format(
        project.name, current_date)
    message['From'] = from_address
    message['To'] = ', '.join(to_addresses)
    if cc_addresses:
        message['Cc'] = ', '.join(cc_addresses)

    text_part = MIMEText(rendered_text.encode('utf-8'), 'plain')
    html_part = MIMEText(rendered_html.encode('utf-8'), 'html')

    message.attach(text_part)
    message.attach(html_part)

    if cc_addresses:
        to_addresses.extend(cc_addresses)

    try:
        smtp_conn = smtplib.SMTP('localhost', timeout=300)
        smtp_conn.sendmail(from_address, to_addresses, message.as_string())
        smtp_conn.quit()
    except smtplib.SMTPException as ex:
        print >> sys.stderr, 'WARNING: Email could not be sent:'
        print >> sys.stderr, ex


def write_rendered_files(rendered_html, rendered_text, current_date):
    '''Writes the rendered files out to disk.

    Currently, this creates a AsanaMailer_[Date].html and *.markdown file.

    :param rendered_html: The rendered HTML template.
    :param rendered_text: The rendered text template.
    :param current_date: The current date.
    '''
    with codecs.open(
            'AsanaMailer_{0}.html'.format(current_date), 'w', 'utf-8') as (
            html_file):
        html_file.write(rendered_html)
    with codecs.open(
            'AsanaMailer_{0}.markdown'.format(current_date), 'w', 'utf-8') as (
            markdown_file):
        markdown_file.write(rendered_text)


def main():
    '''The main function for generating the mailer.

    Based on the arguments, the mailer generates a Project object with its
    appropriate Section and Tasks objects, and then renders templates
    accordingly. This can either be written out to two files, or can be mailed
    out using a SMTP server running on localhost.
    '''
    parser = argparse.ArgumentParser(
        description='Generates an email template for an Asana project',
        fromfile_prefix_chars='@')
    parser.add_argument('project_id', help='the asana project id')
    parser.add_argument('api_key', help='your asana api key')
    parser.add_argument(
        '-c', '--completed', action='store_true', dest='keep_completed',
        help='show non-archived tasks completed within the last 36 hours')
    parser.add_argument(
        '-f', '--filter-tags', nargs='+', dest='tag_filters', default=[],
        metavar='TAG', help='Tags to filter tasks on')
    parser.add_argument(
        '-s', '--filter-sections', nargs='+', dest='section_filters',
        default=[], metavar='SECTION', help='Sections to filter tasks on')
    parser.add_argument(
        '--html-template', default='Project_Styled.html',
        help='a custom template to use for the html portion')
    parser.add_argument(
        '--text-template', default='Project.markdown',
        help='a custom template to use for the plaintext portion')
    email_group = parser.add_argument_group(
        'email', 'arguments for sending emails')
    email_group.add_argument(
        '--to-addresses', nargs='+', metavar='ADDRESS',
        help="the 'To:' addresses for the outgoing email")
    email_group.add_argument(
        '--cc-addresses', nargs='+', metavar='ADDRESS',
        help="the 'Cc:' addresses for the outgoing email")
    email_group.add_argument(
        '--from-address', metavar='ADDRESS',
        help="the 'From:' address for the outgoing email")

    args = parser.parse_args()

    if bool(args.from_address) != bool(args.to_addresses):
        parser.error(
            "'To:' and 'From:' address are required for sending email")

    asana = Asana(args.api_key)
    filters = frozenset((unicode(filter) for filter in args.tag_filters))
    section_filters = frozenset(
        (unicode(section) for section in args.section_filters))
    project = Project.create_project(
        asana, args.project_id, filters=filters,
        section_filters=section_filters,
        keep_completed=args.keep_completed)
    current_date = str(datetime.date.today())
    rendered_html, rendered_text = generate_templates(
        project, args.html_template, args.text_template, current_date)

    if args.to_addresses and args.from_address:
        send_email(
            project, args.from_address, args.to_addresses, args.cc_addresses,
            rendered_html, rendered_text, current_date)
    else:
        write_rendered_files(rendered_html, rendered_text, current_date)


if __name__ == '__main__':
    main()
