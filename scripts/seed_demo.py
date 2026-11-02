"""Idempotently add sample fleet, shipment, and trip records to the local database."""

import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import Driver, SessionLocal, Shipment, Trip, Vehicle


VEHICLES = [
    {"plate_number": "DEMO-KA-1021", "model": "Tata 407 Gold", "capacity_kg": 3500},
    {"plate_number": "DEMO-KA-2042", "model": "Mahindra Bolero Pik-Up", "capacity_kg": 1500},
    {"plate_number": "DEMO-KA-3083", "model": "Ashok Leyland Dost+", "capacity_kg": 1250},
]
DRIVERS = [
    {"name": "Meera Reddy", "license_number": "DEMO-LIC-1021", "phone": "9000001021"},
    {"name": "Kiran Shetty", "license_number": "DEMO-LIC-2042", "phone": "9000002042"},
    {"name": "Naveen Rao", "license_number": "DEMO-LIC-3083", "phone": "9000003083"},
]
SHIPMENTS = [
    {"tracking_number": "DEMO-261102-0001", "customer_name": "Blue Oak Retail", "origin": "Bengaluru", "destination": "Mysuru", "description": "Retail cartons", "status": "pending", "trip_status": "scheduled"},
    {"tracking_number": "DEMO-261102-0002", "customer_name": "Lumen Office Supplies", "origin": "Hubballi", "destination": "Belagavi", "description": "Office equipment", "status": "assigned", "trip_status": "assigned"},
    {"tracking_number": "DEMO-261102-0003", "customer_name": "GreenField Foods", "origin": "Tumakuru", "destination": "Bengaluru", "description": "Packaged food products", "status": "in_transit", "trip_status": "in_transit"},
    {"tracking_number": "DEMO-261102-0004", "customer_name": "Cedar Home Goods", "origin": "Mangaluru", "destination": "Udupi", "description": "Homeware parcel", "status": "delivered", "trip_status": "delivered"},
]


def main() -> None:
    with SessionLocal() as db:
        vehicles = []
        for values in VEHICLES:
            row = db.scalar(select(Vehicle).where(Vehicle.plate_number == values["plate_number"]))
            if row is None:
                row = Vehicle(**values)
                db.add(row)
            vehicles.append(row)

        drivers = []
        for values in DRIVERS:
            row = db.scalar(select(Driver).where(Driver.license_number == values["license_number"]))
            if row is None:
                row = Driver(**values)
                db.add(row)
            drivers.append(row)
        db.flush()

        for index, values in enumerate(SHIPMENTS):
            shipment = db.scalar(select(Shipment).where(Shipment.tracking_number == values["tracking_number"]))
            if shipment is None:
                shipment = Shipment(**{k: v for k, v in values.items() if k not in {"trip_status"}})
                db.add(shipment)
                db.flush()
            trip = db.scalar(select(Trip).where(Trip.shipment_id == shipment.id))
            if trip is None:
                trip = Trip(shipment_id=shipment.id, status=values["trip_status"])
                if index in (1, 2, 3):
                    trip.vehicle_id = vehicles[index - 1].id
                    trip.driver_id = drivers[index - 1].id
                    if values["trip_status"] in {"assigned", "in_transit"}:
                        vehicles[index - 1].status = "assigned"
                        drivers[index - 1].status = "assigned"
                db.add(trip)

        db.commit()
        print("Demo records are ready (existing records were kept).")
        print("Vehicles:", ", ".join(v.plate_number for v in vehicles))
        print("Drivers:", ", ".join(d.name for d in drivers))
        print("Demo shipments:", len(SHIPMENTS), "(pending, assigned, in transit, delivered)")


if __name__ == "__main__":
    main()
