// -----------------------------------------------------------------------------
// This file is part of ABCD.
// 2025 Nicolò Tuccori
// -----------------------------------------------------------------------------

'use strict';

function page_loaded() {
    const utf8decoder = new TextDecoder("utf8");

    const default_time_refresh = 5;
    const default_plot_height = 600;

    var connection_checker = new ConnectionChecker();

    var layout_timeseries = {
        title: 'Time Series Data',
        xaxis: {
            title: 'Time since start (s)',
            type: 'linear',
            domain: [0, 1],
            anchor: 'y',
            autorange: true,
            showspikes: true,
            spikemode: 'across'
        },
        // xaxis2: {
        //     title: 'Absolute Time',
        //     overlaying: 'x',
        //     side: 'top',
        //     tickformat: '%H:%M:%S',
        //     autorange: true,
        //     showspikes: true,
        //     spikemode: 'across',
        //     type: 'date'
        // },
        yaxis: {
            title: 'Value',
            autorange: true,
            showspikes: true,
            spikemode: 'across'
        },
        margin: {
            t: 80,
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
    var channel_labels = [];

    let visibleChannels = new Set(); // Channels currently shown
    let hiddenChannels = new Set(); // Channels currently shown

    const module_name = String($('input#module_name').val());
    
    console.log("Module name: " + module_name);

    $("#time_refresh").val(default_time_refresh);

    var old_status = {"timestamp": "###"};

    function on_status(message) {
        
        const decoded_string = utf8decoder.decode(message);
        const status = JSON.parse(decoded_string);

        connection_checker.beat();

        if (status.hasOwnProperty("active_channels")) {
            if (active_channels.length == 0) {
                updateChannelList(status.active_channels);
            }
            active_channels = status.active_channels;
            
            // updateChannelList(active_channels);
            // update_selector(active_channels);
        }
    }

    function add_to_timeseries(message) {
        message.data.forEach(channelObj => {

            const id = channelObj.id;
            if (!series_data[id]) {
                series_data[id] = { x: [], x2: [], y: [] };
            }
            
            let labelObj;
            try {
                labelObj = typeof channelObj.label === "string" ? JSON.parse(channelObj.label) : channelObj.label;
                if (!channel_labels[id]) {
                    channel_labels[id] = `( ${labelObj.portID}, ${labelObj.slaveID}, ${labelObj.moduleID}, ${labelObj.sensorID}, ${labelObj.sensorPlace} )`;
                }
            } catch (e) {
                console.error(`Failed to parse label JSON for channel ${id}`, e);
            }

            let plotObj;
            try {
                plotObj = JSON.parse(channelObj.plot);
            } catch (e) {
                console.error(`Failed to parse plot JSON for channel ${id}`, e);
                return;
            }

            plotObj.data.forEach(point => {
                
                const t_iso = new Date(point[0] * 1000).toISOString();

                // Push date and value for plotting
                series_data[id].x.push(point[1]);
                series_data[id].x2.push(t_iso);
                series_data[id].y.push(point[2]);
            });
        });
    }

    function create_plot() {
        Plotly.newPlot('plot_timeseries', [], layout_timeseries, config_timeseries);
    }

    function update_plot(force) {
        const force_update = !_.isNil(force);
        const now = dayjs();
        const diff = next_update_plot.diff(now, "seconds");

        if (diff <= 0 || force_update) {
            let data = [];

            // active_channels.forEach(ch => {
            visibleChannels.forEach(ch => {
                const checkbox = document.getElementById(`ch-${ch}`);
                if (checkbox) {
                    if (series_data[ch]) {
                        data.push({
                            x: series_data[ch].x,
                            y: series_data[ch].y,
                            mode: 'lines+markers',
                            name: channel_labels[ch],
                            type: 'scatter'
                        });

                        // data.push({
                        //     x: series_data[ch].x2,
                        //     y: series_data[ch].y,
                        //     mode: 'lines',
                        //     name: channel_labels[ch] + ' (abs)',
                        //     type: 'scatter',
                        //     xaxis: 'x2',
                        //     showlegend: false  // prevent legend clutter
                        // });
                    }
                }
            });

            // Compute ranges for axes
            // let allSeconds = [];
            // visibleChannels.forEach(ch => {
            //     if (series_data[ch]) allSeconds.push(...series_data[ch].x);
            // });

            // if (allSeconds.length > 0) {
            //     const minSec = Math.min(...allSeconds);
            //     const maxSec = Math.max(...allSeconds);

            //     // const minDate = new Date((startTime + minSec) * 1000).toISOString();
            //     // const maxDate = new Date((startTime + maxSec) * 1000).toISOString();

            //     layout_timeseries.xaxis.range = [minSec, maxSec];
            //     layout_timeseries.xaxis2.range = [minDate, maxDate];
            // }

            Plotly.react('plot_timeseries', data, layout_timeseries);

            const refresh_time = Number($("#time_refresh").val()) || default_time_refresh;
            next_update_plot = dayjs().add(refresh_time, "seconds");
        }
    }

    function updateChannelList(channels) {
        const container = document.getElementById('channel_list');
        container.innerHTML = ''; // Clear existing

        channels.forEach(ch => {
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `ch-${ch}`;
            checkbox.checked = true;
            checkbox.addEventListener('change', () => toggleChannel(ch, checkbox.checked));

            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.textContent = ` ${channel_labels[ch] || `Channel ${ch}`}`;

            const wrapper = document.createElement('div');
            wrapper.appendChild(checkbox);
            wrapper.appendChild(label);

            container.appendChild(wrapper);
            visibleChannels.add(ch);
        });

        // Initial render
        update_plot();
    }

    function toggleChannel(channel, isVisible) {
        if (isVisible) {
            visibleChannels.add(channel);
            if (hiddenChannels.has(channel))
                hiddenChannels.delete(channel);
        } else {
            visibleChannels.delete(channel);
            hiddenChannels.add(channel);
        }

        // Add any new active channels that aren't yet in visibleChannels
        active_channels.forEach(ch => {
            if (!visibleChannels.has(ch) && !hiddenChannels.has(ch)) {
                visibleChannels.add(ch);
                const checkbox = document.getElementById(`ch-${ch}`);
                if (checkbox) checkbox.checked = true; // tick if not already
            }
        });

        refreshPlotNow();
    }
    
    function on_data(message) {
        
        let parsed;
        try {
            parsed = typeof message === "string" ? JSON.parse(message) : message;
        } catch (e) {
            console.error("Failed to parse message", e);
            return;
        }

        const decoded_string = utf8decoder.decode(message);
        const new_timeseries = JSON.parse(decoded_string);
        add_to_timeseries(new_timeseries);
        // update_selector(active_channels);
        if (active_channels.length == 0) updateChannelList(active_channels);
        update_plot();
    }
    
    socket_io.on("connect", socket_io_connection(socket_io, module_name, on_status, update_events_log(), on_data));

    window.setInterval(() => {
        connection_checker.display();
    }, 1000);

    function refreshPlotNow() {
        const refresh_time = Number($("#time_refresh").val()) || default_time_refresh;
        next_update_plot = dayjs().add(refresh_time, "seconds");
        update_plot(true);
    }
    $("#time_refresh").on('change', refreshPlotNow);

    // Resize handling to keep plot responsive
    var observer = new MutationObserver(function () {
        window.dispatchEvent(new Event('resize'));
    });
    observer.observe($("#plot_timeseries")[0], { attributes: true });
    $("#plot_timeseries").css("height", default_plot_height + "px");

    create_plot();
}

$(page_loaded);