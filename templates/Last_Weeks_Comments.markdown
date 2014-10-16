{% extends "Project.markdown" %}
{% block comment_block %}
{% if task.comments %}
  * Comments:

  {% for comment in task.comments|comments_within_lookback(current_time_utc, 168)|reverse %}
{{ comment.text|wordwrap|indent(6, True) }} - {{ comment.created_by.name }} ({{ comment.created_at|as_date }})

  {% endfor %}

{% endif %}
{% endblock %}
