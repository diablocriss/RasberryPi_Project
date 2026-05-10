#pragma once
#include "booking.h"

int storage_init(const char *db_path);
void storage_close(void);

int storage_room_list(Room **out, int *count);
int storage_room_free_list(Room *list);

int storage_booking_insert(const Booking *b);
int storage_booking_cancel(int booking_id);
int storage_booking_list(Booking **out, int *count);
int storage_availability(const char *check_in,
                         const char *check_out,
                         int **occupied_ids, int *count);
int storage_conflict_check(int room_id,
                           const char *check_in,
                           const char *check_out);
void booking_free_int_list(int *p);
