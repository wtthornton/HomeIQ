"""Test fixtures for Blueprint Index Service."""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.models import Base

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally


@pytest_asyncio.fixture
async def db_session():
    """Create PostgreSQL database session for testing."""
    test_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq_test",
    )
    engine = create_async_engine(
        test_url,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_blueprint_yaml():
    """Sample blueprint YAML for testing."""
    return '''
blueprint:
  name: Motion-Activated Light
  description: Turn on a light when motion is detected
  domain: automation
  input:
    motion_sensor:
      name: Motion Sensor
      description: The motion sensor to use
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    target_light:
      name: Target Light
      description: The light to control
      selector:
        entity:
          domain: light
    no_motion_wait:
      name: Wait Time
      description: Time to wait before turning off
      default: 120
      selector:
        number:
          min: 0
          max: 3600
          unit_of_measurement: seconds

trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: "on"

action:
  - service: light.turn_on
    target:
      entity_id: !input target_light
  - wait_for_trigger:
      - platform: state
        entity_id: !input motion_sensor
        to: "off"
  - delay: !input no_motion_wait
  - service: light.turn_off
    target:
      entity_id: !input target_light
'''


@pytest.fixture
def sample_security_blueprint_yaml():
    """Sample security blueprint YAML for testing."""
    return '''
blueprint:
  name: Door Alert Notification
  description: Send notification when door opens while away
  domain: automation
  input:
    door_sensor:
      name: Door Sensor
      selector:
        entity:
          domain: binary_sensor
          device_class: door
    notify_service:
      name: Notification Service
      selector:
        text:

trigger:
  - platform: state
    entity_id: !input door_sensor
    to: "on"

condition:
  - condition: state
    entity_id: person.home_owner
    state: not_home

action:
  - service: !input notify_service
    data:
      message: "Door opened while away!"
'''
