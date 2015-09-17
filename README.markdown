# Asana Mailer
Asana Mailer is a script that retrieves metadata from an Asana project via
Asana's REST API to generate a Text and HTML email using Jinja2 templates.

Requires Python 2.7.

## Setup
* `pip install -r requirements.txt` (We recommend using a virtualenv, more on
  [virtualenv][venv] and [pip][pip]).
* `python asana_mailer`

## Features
* Generates an inline CSS HTML email, using a default styled template. Inlining
  can be optionally turned off to help test new template styles.
* Generates a Markdown-compatible plain-text email.
* Allows you to swap out default templates with custom templates (place in
  `templates` directory).
* Can filter tasks based on tags
  * Currently task filtering tests if the set of filters is a subset of the
    tags present on a given task.
* Can list off completed tasks (strikethrough in default template) from the
  last 36 hours (doesn't include archived tasks)
* Allows you to send the email via a local SMTP server, using
  `multipart/alternative` for both templates.
  * Relish in the fact that your friends with plaintext email clients will
    actually get a legible email.
  * Run it regularly via cron.

### Too Many Arguments?
Asana Mailer uses argparse's `fromfile_prefix_chars` to place each of your
command line arguments in a file (one per line, including option switches).
Currently, Asana Mailer uses the '`@`' symbol for this prefix. More information
here:

[Python 2.7: argparse `fromfile_prefix_chars`][fromfile_prefix_chars]

[fromfile_prefix_chars]:http://docs.python.org/2.7/library/argparse.html#fromfile-prefix-chars
[venv]: http://www.virtualenv.org/en/latest/
[pip]: http://www.pip-installer.org/en/latest/

## Example

The standard way to use Asana Mailer to filter down the tasks and sections
you're interested in sending info about, and then use a local SMTP server +
cron to send an email. Alternatively, you can send the HTML and Text portions
of the email via some other process using the generated Markdown/Text and HTML
files. Here's an example for an evolving project:

1. I want to send out a daily email with status updates for the "Bugs 1.1.0"
   section of my Asana project for a given milestone. I want this to be sent
   out at 13:30 every weekday before our daily standup.

    Create the following file `awesome_webapp.args` (without the annotations). Note
    one argument or switch per line:

        1234567890 [My Project ID]
        aoeuhtns',.pgcrl;qjkbmwv [My API Key in Asana]
        -s [Filter by section]
        Bugs 1.1.0 [Name of the section]
        --to-addresses
        Example Distribution List <example_list@example.com>
        --from-address
        Example Meeting Owner <example@example.com>

    Create a cron entry similar to the following:

        30 13 * * 1-5 python asana_mailer.py @awesome_webapp.args > /dev/null 2>&1

2. Alright, so I want to keep recently completed tasks (within the last 36
   hours below) for those who are going to receive the emails but aren't
   attending the standup, and I'd also like to filter out all tasks except user
   visible bug tasks tagged with "user_concern".

    Modify `awesome_webapp.args` to be the following:

        1234567890
        aoeuhtns',.pgcrl;qjkbmwv
        -s
        Bugs 1.1.0
        -f [Filter by tag]
        user_concern [Name of the tag]
        -c [Keep recently completed tasks]
        36
        --to-addresses
        Example Distribution List <example_list@example.com>
        --from-address
        Example Meeting Owner <example@example.com>

3. Finally, we've realized that it's best to have some of the core developers
   always explicitly CC'd on the email, as they filter emails to the
   distribution list normally and sometimes miss the standup notes before the
   meeting. Also, while the standard HTML template is decent, we'd like to
   simplify it even further by writing our own Jinja2 template.

    After template creation, modify `awesome_webapp.args` to be the following:

        1234567890
        aoeuhtns',.pgcrl;qjkbmwv
        -s
        Bugs 1.1.0
        -f
        user_concern
        -c
        36
        --to-addresses
        Example Distribution List <example_list@example.com>
        --cc-addresses
        Dev One <dev1@example.com>
        Dev Two <dev2@example.com>
        --from-address
        Example Meeting Owner <example@example.com>
        --html-template
        Project_Awesome_Template.html [Must reside in templates directory]

    And there you go, you have a customized workflow for better dissemination
    of information tracked in Asana. It's best to start with a few arguments
    and iterate slowly without sending emails until you're satisfied with the
    results, and then setup the addresses and cronjob.

### Templates
The templates use Jinja2 as their templating language, and have access to
the Project object as well as the current date. Feel free to customize your own
template for use with your project.


## Usage

    usage: asana_mailer.py [-h] [-i] [-c HOURS] [-f TAG [TAG ...]]
                          [-s SECTION [SECTION ...]]
                          [--html-template HTML_TEMPLATE]
                          [--text-template TEXT_TEMPLATE]
                          [--mail-server HOSTNAME]
                          [--to-addresses ADDRESS [ADDRESS ...]]
                          [--cc-addresses ADDRESS [ADDRESS ...]]
                          [--from-address ADDRESS]
                          project_id api_key

    Generates an email template for an Asana project

    positional arguments:
      project_id            the asana project id
      api_key               your asana api key

    optional arguments:
      -h, --help            show this help message and exit
      -i                    skip inlining CSS
      -c HOURS, --completed HOURS
                            show non-archived tasks completed within the past
                            hours specified
      -f TAG [TAG ...], --filter-tags TAG [TAG ...]
                            tags to filter tasks on
      -s SECTION [SECTION ...], --filter-sections SECTION [SECTION ...]
                            sections to filter tasks on
      --html-template HTML_TEMPLATE
                            a custom template to use for the html portion
      --text-template TEXT_TEMPLATE
                            a custom template to use for the plaintext portion

    email:
      arguments for sending emails

      --mail-server HOSTNAME
                            the hostname of the mail server to send email from
                            (default: localhost)
      --to-addresses ADDRESS [ADDRESS ...]
                            the 'To:' addresses for the outgoing email
      --cc-addresses ADDRESS [ADDRESS ...]
                            the 'Cc:' addresses for the outgoing email
      --from-address ADDRESS
                            the 'From:' address for the outgoing email

## License


**Asana Mailer** is made available under the Apache 2.0 License.

>Copyright 2013 Palantir Technologies
>
>Licensed under the Apache License, Version 2.0 (the "License");
>you may not use this file except in compliance with the License.
>You may obtain a copy of the License at
>
><http://www.apache.org/licenses/LICENSE-2.0>
>
>Unless required by applicable law or agreed to in writing, software
>distributed under the License is distributed on an "AS IS" BASIS,
>WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
>See the License for the specific language governing permissions and
>limitations under the License.

### Questions?
Feel free to [file an issue](https://github.com/palantir/asana_mailer/issues/new).
