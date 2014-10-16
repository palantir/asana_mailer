{% extends "Project.markdown" %}
{% block comment_block %}
{% if task.latest_comment %}
* Last Comment: {{ task.latest_comment.text }} - {{ task.latest_comment.created_by.name }}
{% endif %}
{% endblock %}
