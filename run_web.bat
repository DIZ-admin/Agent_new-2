@echo off
echo Starting ERNI Photo Processor Web Interface...
docker-compose build web
docker-compose up web
