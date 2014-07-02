function graph_data(series_data, request_params, id) {
	// instantiate a Rickshaw graph

	var graph = new Rickshaw.Graph( {
		element: document.getElementById(id),
		width: 960,
		height: 500,
		renderer: 'line',
		series: [
			{
				color: "#c05020",
				data: series_data,
				name: request_params['title']
			}
		]
	} );

	graph.render();

	var hoverDetail = new Rickshaw.Graph.HoverDetail( {
		graph: graph
	} );

	var legend = new Rickshaw.Graph.Legend( {
		graph: graph,
		element: document.getElementById('legend')

	} );

	var shelving = new Rickshaw.Graph.Behavior.Series.Toggle( {
		graph: graph,
		legend: legend
	} );

	var axes = new Rickshaw.Graph.Axis.Time( {
		graph: graph
	} );
	axes.render();
}
