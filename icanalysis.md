//__view__:icanalysis_view//
<h2>{{ plugin.name }}</h2>

{{ plugin.description|safe }}

<h2>Submit a Job</h2>

{% if jobs %}
<h3>Order Your Trajectories</h3>
<form action = "" method="post">
{% csrf_token %}
<table style="width:100%">
  <col width="93%">
  <col width="7%">
  <tr>
    <th>Protein Name</th>
    <th>Select</th>
  </tr>
  {% for job in jobs %}
  <tr>
    <td>{{ job.pname }}</td>
    <td>
        <input type="radio" name="job" value="{{ job.jobid }}"><br>
        </td>
  </tr>
  {% endfor %}
</table>
<input type="submit" name="job_selected" value="Select">
</form>
{% else %}
You haven't ran wQAA yet! Go [run](/wqaa/) something!
{% endif %}
