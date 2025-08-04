const zmq = require("zeromq");

async function run() {
  const sock = new zmq.Subscriber();

  // Connect to the publisher endpoint
  sock.connect("tcp://127.0.0.1:16188");
  console.log("Subscriber connected to tcp://127.0.0.1:16188");

  // Subscribe to the prefix "data_spect_timeseries" to receive all matching topics
  sock.subscribe("data_spect_timeseries");
  console.log("Subscribed to topic prefix: data_spect_timeseries");

  for await (const [msg] of sock) {
    // The message will be a Buffer, convert to string
    const fullMessage = msg.toString();

    // The topic is up to the first space, the rest is JSON payload
    const spaceIndex = fullMessage.indexOf(" ");
    if (spaceIndex === -1) {
      console.warn("Received malformed message:", fullMessage);
      continue;
    }

    const topic = fullMessage.slice(0, spaceIndex);
    const jsonString = fullMessage.slice(spaceIndex + 1);

    console.log("Received topic:", topic);

    try {
      const data = JSON.parse(jsonString);

      console.log("Parsed JSON data:", data);

      // If the "plot" field inside data is a JSON string, parse it again
      if (data.data && Array.isArray(data.data)) {
        for (const entry of data.data) {
          if (entry.plot) {
            entry.plot = JSON.parse(entry.plot);
          }
        }
      }

      // Now you have fully parsed data with nested JSON objects
      // Do whatever you want here with the data

    } catch (err) {
      console.error("Error parsing JSON:", err);
    }
  }
}

run().catch(err => console.error("Subscriber error:", err));
