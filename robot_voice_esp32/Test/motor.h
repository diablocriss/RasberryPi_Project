#pragma once
#include <Arduino.h>

inline void motor_init()                            {}
inline void motor_tick()                            {}
inline void motor_stop()                            {}
inline void motor_forward(int speed, int time_ms)   {}
inline void motor_backward(int speed, int time_ms)  {}
inline void motor_turn_left(int speed, int time_ms) {}
inline void motor_turn_right(int speed, int time_ms){}

