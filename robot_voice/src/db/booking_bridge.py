from __future__ import annotations

import ctypes
from ctypes import POINTER, Structure, byref, c_char, c_char_p, c_int, c_int64
from pathlib import Path


class Booking(Structure):
    _fields_ = [
        ("booking_id", c_int),
        ("guest_name", c_char * 64),
        ("email", c_char * 64),
        ("check_in_date", c_char * 12),
        ("check_out_date", c_char * 12),
        ("number_of_guests", c_int),
        ("room_id", c_int),
        ("room_number", c_char * 8),
        ("room_type", c_char * 16),
        ("created_at", c_int64),
        ("status", c_char * 16),
    ]


class Room(Structure):
    _fields_ = [
        ("room_id", c_int),
        ("room_number", c_char * 8),
        ("room_type", c_char * 16),
        ("description", c_char * 128),
    ]


def _decode(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")


def _encode(text: str, size: int) -> bytes:
    return (text or "").encode("utf-8")[: max(0, size - 1)]


class BookingLib:
    def __init__(self, so_path: str | Path):
        self.so_path = Path(so_path).expanduser()
        if not self.so_path.exists():
            raise FileNotFoundError(f"Shared library not found: {self.so_path}")
        self._lib = ctypes.CDLL(str(self.so_path))
        self._setup_signatures()

    def _setup_signatures(self) -> None:
        self._lib.storage_init.argtypes = [c_char_p]
        self._lib.storage_init.restype = c_int
        self._lib.storage_close.argtypes = []
        self._lib.storage_close.restype = None
        self._lib.booking_create.argtypes = [POINTER(Booking)]
        self._lib.booking_create.restype = c_int
        self._lib.booking_cancel.argtypes = [c_int]
        self._lib.booking_cancel.restype = c_int
        self._lib.booking_list.argtypes = [POINTER(POINTER(Booking)), POINTER(c_int)]
        self._lib.booking_list.restype = c_int
        self._lib.booking_free_list.argtypes = [POINTER(Booking)]
        self._lib.booking_free_list.restype = None
        self._lib.booking_check_conflict.argtypes = [c_int, c_char_p, c_char_p]
        self._lib.booking_check_conflict.restype = c_int
        self._lib.storage_room_list.argtypes = [POINTER(POINTER(Room)), POINTER(c_int)]
        self._lib.storage_room_list.restype = c_int
        self._lib.storage_room_free_list.argtypes = [POINTER(Room)]
        self._lib.storage_room_free_list.restype = c_int
        self._lib.storage_availability.argtypes = [
            c_char_p,
            c_char_p,
            POINTER(POINTER(c_int)),
            POINTER(c_int),
        ]
        self._lib.storage_availability.restype = c_int
        self._lib.booking_free_int_list.argtypes = [POINTER(c_int)]
        self._lib.booking_free_int_list.restype = None

    def storage_init(self, db_path: str | Path) -> int:
        return int(self._lib.storage_init(str(Path(db_path).expanduser()).encode("utf-8")))

    def storage_close(self) -> None:
        self._lib.storage_close()

    def create_booking(
        self,
        guest_name: str,
        email: str,
        check_in: str,
        check_out: str,
        guests: int,
        room_id: int,
    ) -> int:
        booking = Booking()
        booking.guest_name = _encode(guest_name, 64)
        booking.email = _encode(email, 64)
        booking.check_in_date = _encode(check_in, 12)
        booking.check_out_date = _encode(check_out, 12)
        booking.number_of_guests = guests
        booking.room_id = room_id
        return int(self._lib.booking_create(byref(booking)))

    def cancel_booking(self, booking_id: int) -> int:
        return int(self._lib.booking_cancel(booking_id))

    def list_bookings(self) -> list[dict[str, object]]:
        bookings_ptr = POINTER(Booking)()
        count = c_int(0)
        rc = int(self._lib.booking_list(byref(bookings_ptr), byref(count)))
        if rc != 0:
            raise RuntimeError(f"booking_list failed with code {rc}")
        try:
            return [
                {
                    "booking_id": bookings_ptr[i].booking_id,
                    "guest_name": _decode(bookings_ptr[i].guest_name),
                    "email": _decode(bookings_ptr[i].email),
                    "check_in_date": _decode(bookings_ptr[i].check_in_date),
                    "check_out_date": _decode(bookings_ptr[i].check_out_date),
                    "number_of_guests": bookings_ptr[i].number_of_guests,
                    "room_id": bookings_ptr[i].room_id,
                    "room_number": _decode(bookings_ptr[i].room_number),
                    "room_type": _decode(bookings_ptr[i].room_type),
                    "created_at": bookings_ptr[i].created_at,
                    "status": _decode(bookings_ptr[i].status),
                }
                for i in range(count.value)
            ]
        finally:
            if bookings_ptr:
                self._lib.booking_free_list(bookings_ptr)

    def list_rooms(self) -> list[dict[str, object]]:
        rooms_ptr = POINTER(Room)()
        count = c_int(0)
        rc = int(self._lib.storage_room_list(byref(rooms_ptr), byref(count)))
        if rc != 0:
            raise RuntimeError(f"storage_room_list failed with code {rc}")
        try:
            return [
                {
                    "room_id": rooms_ptr[i].room_id,
                    "room_number": _decode(rooms_ptr[i].room_number),
                    "room_type": _decode(rooms_ptr[i].room_type),
                    "description": _decode(rooms_ptr[i].description),
                }
                for i in range(count.value)
            ]
        finally:
            if rooms_ptr:
                self._lib.storage_room_free_list(rooms_ptr)

    def check_availability(self, check_in: str, check_out: str) -> list[int]:
        occupied_ptr = POINTER(c_int)()
        count = c_int(0)
        rc = int(
            self._lib.storage_availability(
                check_in.encode("utf-8"),
                check_out.encode("utf-8"),
                byref(occupied_ptr),
                byref(count),
            )
        )
        if rc != 0:
            raise RuntimeError(f"storage_availability failed with code {rc}")
        try:
            return [int(occupied_ptr[i]) for i in range(count.value)] if occupied_ptr else []
        finally:
            if occupied_ptr:
                self._lib.booking_free_int_list(occupied_ptr)

    def check_conflict(self, room_id: int, check_in: str, check_out: str) -> bool:
        rc = int(
            self._lib.booking_check_conflict(
                room_id,
                check_in.encode("utf-8"),
                check_out.encode("utf-8"),
            )
        )
        if rc < 0:
            raise RuntimeError(f"booking_check_conflict failed with code {rc}")
        return rc == 1
