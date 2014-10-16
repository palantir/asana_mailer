# {{ project.name }} Daily Actions {{ current_date }}
{% if project.description %}
#### {{ project.description }}
{% endif %}
{% block pre_block %}
{% endblock %}
{% block tasks_block %}
{% for section in project.sections %}
## {{ section.name }}
{% for task in section.tasks %}
* {{ '[DONE]: ' if task.completed }}{{ task.name }} - {{ task.assignee if task.assignee else 'Unassigned' }}{{ ' (%s)'|format(task.tags|join(', ')) if task.tags }}
  {% if task.due_date %}
  * Due Date: {{ task.due_date }}
  {% endif %}
  {% block comment_block scoped %}
  {% endblock %}
  {% if task.description %}
  * Description:

{{ task.description|wordwrap|indent(6, True) }}

  {% endif %}
{% endfor %}

{% endfor %}
{% endblock %}
{% block post_block %}
{% endblock %}
