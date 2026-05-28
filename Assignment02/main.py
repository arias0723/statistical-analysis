from util import *
from simulator import Simulator
from queue_model import QueueModel


if __name__ == "__main__":
    random.seed(42)
    sim = Simulator()

    # M/M/1/inf/FIFO queue
    # Arrival rate: 2 per unit time, Service rate: 3 per unit time
    q1 = QueueModel(
        sim=sim, 
        name="Queue1", 
        arrival_dist=exponential(2.0), 
        service_dist=exponential(3.0),
        servers=1
    )
    
    q1.start_generator()
    
    print("Running simulation...")
    sim.run(until=1000000.0)
    
    print(f"Results for {q1.name}:")
    print(f"Processed: {q1.entities_processed}")
    print(f"Dropped: {q1.entities_dropped}")
