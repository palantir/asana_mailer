# Asana Mailer
Asana Mailer is a script that retrieves metadata from an Asana project via
Asana's REST API to generate a plaintext and HTML email using Jinja2 templates.

Requires Python 2.7.

## Features
* Generates an inline CSS HTML email, using a default styled template.
* Generates a Markdown-compatible plain-text email.
* Allows you to swap out default templates with custom templates (place in
  templates folder).
* Can filter tasks based on tags
  * Tasks must contain all tags specified.
* Can list off completed tasks (strikethrough in default template) from the
  last 36 hours (doesn't include archived tasks)
* Allows you to send the email via a local SMTP server, using
  multipart/alternative for both templates.
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

## Usage

    (venv)jgoodnow-mbp:asana_mailer jgoodnow$ python asana_mailer.py -h
    usage: asana_mailer.py [-h] [-c] [-f TAG [TAG ...]]
                           [--html-template HTML_TEMPLATE]
                           [--text-template TEXT_TEMPLATE]
                           [--to-addresses ADDRESS [ADDRESS ...]]
                           [--from-address ADDRESS]
                           project_id api_key

    Generates an email template for an Asana project

    positional arguments:
      project_id            the asana project id
      api_key               your asana api key

    optional arguments:
      -h, --help            show this help message and exit
      -c, --completed       show non-archived tasks completed within the last 36
                            hours
      -f TAG [TAG ...], --filter-tags TAG [TAG ...]
                            Tags to filter tasks on
      --html-template HTML_TEMPLATE
                            a custom template to use for the html portion
      --text-template TEXT_TEMPLATE
                            a custom template to use for the plaintext portion

    email:
      arguments for sending emails

      --to-addresses ADDRESS [ADDRESS ...]
                            the 'To:' addresses for the outgoing email
      --from-address ADDRESS
                            the 'From:' address for the outgoing email
