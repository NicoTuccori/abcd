// -----------------------------------------------------------------------------
// This file is part of ABCD.
// 2025 Nicolò Tuccori
// -----------------------------------------------------------------------------

'use strict';

function page_loaded() {
    const utf8decoder = new TextDecoder("utf8");

    const default_time_refresh = 5;
    const default_plot_height = 900;

    var connection_checker = new ConnectionChecker();

    const layout_timeseries = {
        title: 'Time Series Data',
        grid: { rows: 1, columns: 1 },
        
        // Main x-axis (seconds)
        xaxis: {
            title: 'Seconds from start',
            domain: [0, 1],
            anchor: 'y',
            side: 'bottom',
            position: 0.1,  // position is between 0 (bottom) and 1 (top)
            showspikes: true,
            spikemode: 'across'
        },

        // Second x-axis (date/time), below the main one
        // xaxis2: {
        //     title: 'Date / Time',
        //     domain: [0, 1],
        //     anchor: 'free',
        //     position: 0.05,  // put at very bottom
        //     side: 'bottom',
        //     tickvals: [],   // to be filled dynamically
        //     ticktext: [],
        //     tickangle: 0
        // },

        yaxis: {
            title: 'Value',
            domain: [0.15, 1], // leave space for two x-axes below
            anchor: 'x',
            autorange: true,
            showspikes: true,
            spikemode: 'across'
        },

        margin: {
            t: 80,
            b: 80,  // extra space for double x-axis
            l: 70,
            r: 10
        },

        hovermode: 'closest',
        legend: { x: 1, xanchor: 'right', y: 1, yanchor: 'top' }
    };

    const config_timeseries = {
        responsive: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };

    var socket_io = io();

    var next_update_plot = dayjs().add(-10, "seconds");

    var series_data = {};  // Store time series arrays per channel
    var active_channels = [];
    var channel_plottypes = {};
    var channel_titles = {};
    var channel_labels = [];

    var start_unix = null;

    const module_name = String($('input#module_name').val());

    $("#time_refresh").val(default_time_refresh);

    var old_status = {"timestamp": "###"};
    var last_spect_config = null;

    var spect_config_editor = ace.edit("online_editor");
    spect_config_editor.setTheme("ace/theme/github");
    spect_config_editor.setShowPrintMargin(false);
    spect_config_editor.setOptions({"fontFamily": '"Fira Mono"'});

    spect_config_editor.getSession().setMode("ace/mode/json");
    spect_config_editor.getSession().setTabSize(4);
    spect_config_editor.getSession().setUseSoftTabs(true);

    spect_config_editor.container.style.lineHeight = 2;
    spect_config_editor.renderer.updateFontSize();
    spect_config_editor.resize();

    function on_status(message) {
        const new_status = JSON.parse(utf8decoder.decode(message));
        connection_checker.beat();

        if (new_status["timestamp"] !== old_status["timestamp"])
        {
            old_status = new_status;

            //console.log("Updating Speccalc status");

            if (new_status.hasOwnProperty("config")) {
                last_spect_config = new_status["config"];
            }

            if (Array.isArray(new_status.active_channels)) {

                // Initialize or update channel_plottypes
                for (const ch of new_status.active_channels) {
                    // Find matching config channel by id
                    const configChannel = new_status.config.channels.find(c => c && c.id === ch);
                    if (configChannel) {
                        channel_plottypes[ch] = configChannel.plotType;
                        channel_titles[ch] = configChannel.label;

                        if (channel_plottypes[ch] == "abtp2_temperature") {
                            const plotDiv = document.getElementById('plot_timeseries');
                            plotDiv.layout.title.text = channel_titles[ch];
                        }

                    }
                }
            }
        }
    }

    function add_to_timeseries(message) {
        message.data.forEach(channelObj => {
            const ch = channelObj.id;
            var id = ch;

            if (channel_plottypes[ch] == "abtp2_temperature") id = channelObj.stream;

            if (!series_data[id]) series_data[id] = { x: [], y: [] };
            if (!active_channels.includes(id)) active_channels.push(id);
            let labelObj;
            labelObj = typeof channelObj.label === "string" ? JSON.parse(channelObj.label) : channelObj.label;
            if (!channel_labels[id]) {
                channel_labels[id] = `( ${labelObj.portID}, ${labelObj.slaveID}, ${labelObj.moduleID}, ${labelObj.sensorID}, ${labelObj.sensorPlace} )`;
            }

            let plotObj;
            plotObj = JSON.parse(channelObj.plot);
            if (start_unix === null) start_unix = plotObj.start_timestamp;
            plotObj.data.forEach(point => {
                series_data[id].x.push(point[0]);
                series_data[id].y.push(point[1]);
            });
            series_data[id].x.push(null);
            series_data[id].y.push(null);
        });
        
    }

    function create_plot() {
        const plotDiv = document.getElementById('plot_timeseries');
        Plotly.newPlot(plotDiv, [], layout_timeseries, config_timeseries);
    }

    function update_plot(force) {
        const force_update = !_.isNil(force) && force;
        const now = dayjs();
        const difference = next_update_plot.diff(now, 'seconds');

        if (difference <= 0 || force_update) {

            let data = [];
            const plotDiv = document.getElementById('plot_timeseries');
            const existingTraces = (plotDiv && plotDiv.data) ? plotDiv.data : [];

            active_channels.forEach((ch, idx) => {
                if (series_data[ch]) {
                    const trace_name = channel_labels[ch];

                    let visible = true;
                    // Check if a trace with this name already exists and preserve its visibility
                    const existing = existingTraces.find(t => t.name === trace_name);
                    if (existing && 'visible' in existing) {
                        visible = existing.visible;
                    }
                    const trace = {
                        x: series_data[ch].x,
                        y: series_data[ch].y,
                        mode: 'lines+markers',
                        name: channel_labels[ch],
                        type: 'scatter',
                        visible: visible,
                        line: {
                            dash: 'dot',  // Try 'dot', 'dash', 'longdash', etc.
                            width: 0.5
                        }
                    };
                    data.push(trace);
                }
            });

            // Compute date ticks...
            // Compute tick labels
            const allSec = [].concat(...data.map(t => t.x));
            if (allSec.length && start_unix !== null) {
                const minX = Math.min(...allSec);
                const maxX = Math.max(...allSec);
                const totalRange = maxX - minX;

                // 10 evenly spaced second ticks
                const secTicks = Array.from({ length: 10 }, (_, i) =>
                    Math.round(minX + (i / 9) * totalRange)
                );

                // 3 datetime ticks: start, middle, end
                const datetimeTicks = [
                    minX,
                    Math.round(minX + totalRange / 2),
                    maxX
                ];

                // Merge and deduplicate
                const tickvals = Array.from(new Set([...secTicks, ...datetimeTicks])).sort((a, b) => a - b);

                // Map to tick labels: seconds or datetime
                const ticktext = tickvals.map(s => {
                    const seconds = `${s}s`;
                    if (datetimeTicks.includes(s)) {
                        const d = new Date((start_unix + s) * 1000);
                        const time = d.toISOString().slice(11, 16); // HH:MM
                        const date = d.toISOString().slice(5, 10);  // MM-DD
                        return `${seconds}<br>${time} ${date}`;
                    } else {
                        return `${seconds}`;
                    }
                });

                layout_timeseries.xaxis.tickvals = tickvals;
                layout_timeseries.xaxis.ticktext = ticktext;
            }

            Plotly.react(plotDiv, data, layout_timeseries);
            Plotly.update(plotDiv, data, layout_timeseries);
            const refresh_time = Number($("#time_refresh").val() || default_time_refresh);
            next_update_plot = dayjs().add(refresh_time, 'seconds');
        }
    }
    
    function on_data(message) {
        const decoded_string = utf8decoder.decode(message);
        const new_timeseries = JSON.parse(decoded_string);
        add_to_timeseries(new_timeseries);
        // if (active_channels.length == 0) updateChannelList(active_channels);
        update_plot();
    }

    function spect_get_config() {
        if (_.isNil(last_spect_config)) {
            spect_config_editor.getSession().setValue(JSON.stringify({"error": "Unable to load spect config"}, null, 4));
            spect_config_editor.gotoLine(0);
        } else {
            spect_config_editor.getSession().setValue(JSON.stringify(last_spect_config, null, 4));
            spect_config_editor.gotoLine(0);
        }
    }
    
    socket_io.on("connect", socket_io_connection(socket_io, module_name, on_status, update_events_log(), on_data));

    window.setInterval(function () {
        connection_checker.display();
    }, 1000);

    function refreshPlotNow() {
        // let refresh_time = Number($("#time_refresh").val());
        // if (isNaN(refresh_time) || refresh_time <= 0) refresh_time = default_time_refresh;
        next_update_plot = dayjs().add(default_time_refresh, "seconds");
        update_plot(true);
    }
    $("#time_refresh").on('change', refreshPlotNow);

    // $("#button_config_send").on("click", send_command(socket_io, 'reconfigure', spec_arguments_reconfigure));
    $("#button_config_get").on("click", spect_get_config);
    // $("#button_config_download").on("click", spec_download_config);

    // Resize handling to keep plot responsive
    var observer = new MutationObserver(function () {
        window.dispatchEvent(new Event('resize'));
    });
    observer.observe($("#plot_timeseries")[0], { attributes: true });
    $("#plot_timeseries").css("height", default_plot_height + "px");

    create_plot();
}

$(page_loaded);