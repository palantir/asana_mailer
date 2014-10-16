{% extends "Project.markdown" %}
{% block comment_block %}
{% if task.comments %}
  {% for comment in task.comments|last_comment %}
  * Last Comment: {{ comment.text }} - {{ comment.created_by.name }}
  {% endfor %}
{% endif %}
{% endblock %}
