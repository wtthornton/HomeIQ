"""Test fixtures for Blueprint Index Service."""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Create in-memory database session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
