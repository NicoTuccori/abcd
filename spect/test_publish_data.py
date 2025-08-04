import zmq
import json

def main():
    context = zmq.Context()
    # Create a subscriber socket
    socket = context.socket(zmq.SUB)
    
    # Connect to your sender's address and port
    socket.connect("tcp://127.0.0.1:16188")  # change if needed

    # Subscribe to the topic prefix you want to listen for
    topic_filter = "data_spect_timeseries"
    socket.setsockopt_string(zmq.SUBSCRIBE, topic_filter)

    print(f"Subscribed to topic prefix: '{topic_filter}'")

    while True:
        # Receive a full message (string)
        message = socket.recv_string()
        
        # The message will be something like:
        # "data_spect_timeseries { ...json... }"
        
        # Split topic and json payload at first space
        topic, json_str = message.split(' ', 1)
        
        # Parse JSON payload
        data = json.loads(json_str)
        
        print(f"Received on topic '{topic}':")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
