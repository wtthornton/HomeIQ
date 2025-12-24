# HA Ingestor System Requirements

This document outlines the hardware and software requirements for deploying the HA Ingestor system in various environments.

## Table of Contents

- [Overview](#overview)
- [Minimum Requirements](#minimum-requirements)
- [Recommended Requirements](#recommended-requirements)
- [Performance Requirements](#performance-requirements)
- [Hardware Specifications](#hardware-specifications)
- [Software Requirements](#software-requirements)
- [Network Requirements](#network-requirements)
- [Storage Requirements](#storage-requirements)
- [Platform Compatibility](#platform-compatibility)
- [Performance Benchmarks](#performance-benchmarks)
- [Scaling Considerations](#scaling-considerations)

## Overview

The HA Ingestor system is designed to be lightweight and efficient, capable of running on modest hardware while scaling to handle high-volume event processing. The system consists of multiple microservices orchestrated via Docker Compose.

### Architecture Components

- **WebSocket Ingestion Service**: Real-time Home Assistant event capture
- **Enrichment Pipeline**: Data processing and weather enrichment
- **InfluxDB**: Time-series database for event storage
- **Admin API**: REST API for system management
- **Data Retention Service**: Automated data lifecycle management
- **Health Dashboard**: Web-based monitoring interface

## Minimum Requirements

### Hardware Minimums

| Component | Minimum Specification | Notes |
|-----------|----------------------|-------|
| **CPU** | 2 cores @ 1.5GHz | ARM64 or x64 architecture |
| **Memory** | 4GB RAM | Shared with host OS |
| **Storage** | 20GB available space | SSD recommended for database |
| **Network** | 100 Mbps ethernet | Stable connection required |

### Software Minimums

| Component | Minimum Version | Notes |
|-----------|----------------|-------|
| **Docker** | 20.10.0+ | Container runtime |
| **Docker Compose** | 2.0.0+ | Service orchestration |
| **Operating System** | Linux 5.4+, Windows 10+, macOS 10.15+ | Host OS compatibility |
| **Python** | 3.8+ | For testing and CLI tools |

### Performance Minimums

| Metric | Minimum Value | Notes |
|--------|---------------|-------|
| **Event Processing** | 100 events/minute | Sustained processing rate |
| **Database Writes** | 50 writes/second | InfluxDB write performance |
| **Memory Usage** | 2GB total | All services combined |
| **Storage I/O** | 10 MB/s | Read/write throughput |

## Recommended Requirements

### Hardware Recommended

| Component | Recommended Specification | Notes |
|-----------|---------------------------|-------|
| **CPU** | 4+ cores @ 2.5GHz | Intel i5/AMD Ryzen 5 or better |
| **Memory** | 8GB+ RAM | 16GB for high-volume scenarios |
| **Storage** | 50GB+ SSD | NVMe SSD for optimal performance |
| **Network** | 1 Gbps ethernet | Low-latency connection preferred |

### Software Recommended

| Component | Recommended Version | Notes |
|-----------|-------------------|-------|
| **Docker** | 24.0+ | Latest stable version |
| **Docker Compose** | 2.20+ | Latest features and performance |
| **Operating System** | Ubuntu 22.04 LTS, Windows 11, macOS 12+ | LTS versions preferred |
| **Python** | 3.11+ | Latest stable version |

### Performance Recommended

| Metric | Recommended Value | Notes |
|--------|------------------|-------|
| **Event Processing** | 1000+ events/minute | High-volume processing |
| **Database Writes** | 500+ writes/second | Optimized InfluxDB performance |
| **Memory Usage** | 4GB total | Comfortable headroom |
| **Storage I/O** | 100+ MB/s | SSD performance |

## Performance Requirements

### Throughput Requirements

#### Event Processing Capacity
- **Minimum**: 100 events/minute sustained
- **Recommended**: 1000+ events/minute sustained
- **Peak**: 5000+ events/minute (burst capacity)

#### Database Performance
- **Write Latency**: < 10ms average
- **Read Latency**: < 50ms average
- **Concurrent Connections**: 50+ simultaneous

#### API Performance
- **Response Time**: < 200ms for health checks
- **Response Time**: < 500ms for data queries
- **Throughput**: 100+ requests/second

### Resource Utilization

#### CPU Usage
- **Idle**: < 5% total CPU usage
- **Normal Load**: < 30% total CPU usage
- **Peak Load**: < 70% total CPU usage

#### Memory Usage
- **InfluxDB**: 1-2GB (primary consumer)
- **WebSocket Ingestion**: 256-512MB
- **Enrichment Pipeline**: 512MB-1GB
- **Admin API**: 256-512MB
- **Other Services**: 256MB each

#### Storage Usage
- **Database Growth**: ~1GB per 100,000 events
- **Log Storage**: ~100MB per day
- **Backup Storage**: 2x database size

## Hardware Specifications

### CPU Requirements

#### Minimum CPU Specifications
- **Architecture**: x64 or ARM64
- **Cores**: 2 physical cores
- **Clock Speed**: 1.5GHz base frequency
- **Cache**: 4MB L3 cache minimum

#### Recommended CPU Specifications
- **Architecture**: x64 (Intel/AMD) or ARM64 (Apple Silicon)
- **Cores**: 4+ physical cores
- **Clock Speed**: 2.5GHz base frequency
- **Cache**: 8MB+ L3 cache
- **Features**: AES-NI, virtualization support

#### High-Performance CPU Specifications
- **Architecture**: x64 server-grade
- **Cores**: 8+ physical cores
- **Clock Speed**: 3.0GHz+ base frequency
- **Cache**: 16MB+ L3 cache
- **Features**: ECC memory support, multiple NUMA nodes

### Memory Requirements

#### Memory Configuration
- **Minimum**: 4GB total system memory
- **Recommended**: 8GB+ total system memory
- **High-Performance**: 16GB+ total system memory
- **Memory Type**: DDR4 or DDR5 recommended

#### Memory Allocation
```
Total Memory: 8GB
├── Host OS: 2GB
├── InfluxDB: 2GB
├── WebSocket Ingestion: 512MB
├── Enrichment Pipeline: 1GB
├── Admin API: 512MB
├── Data Retention: 1GB
└── Other Services: 1GB
```

### Storage Requirements

#### Storage Types
- **Minimum**: HDD (mechanical drive)
- **Recommended**: SSD (solid state drive)
- **Optimal**: NVMe SSD (high-performance)

#### Storage Capacity
- **Minimum**: 20GB available space
- **Recommended**: 50GB+ available space
- **High-Volume**: 100GB+ available space

#### Storage Performance
- **Minimum I/O**: 10 MB/s sequential read/write
- **Recommended I/O**: 100+ MB/s sequential read/write
- **Optimal I/O**: 500+ MB/s sequential read/write

## Software Requirements

### Operating System Compatibility

#### Linux Distributions
- **Ubuntu**: 20.04 LTS, 22.04 LTS, 23.04+
- **Debian**: 11 (Bullseye), 12 (Bookworm)
- **CentOS**: 8, 9
- **RHEL**: 8, 9
- **Fedora**: 37, 38, 39+
- **Arch Linux**: Latest
- **openSUSE**: Leap 15.4+, Tumbleweed

#### Windows Versions
- **Windows 10**: Version 2004+ (Build 19041+)
- **Windows 11**: All versions
- **Windows Server**: 2019, 2022

#### macOS Versions
- **macOS**: 10.15 (Catalina)+
- **macOS**: 11+ (Big Sur)+
- **macOS**: 12+ (Monterey)+
- **macOS**: 13+ (Ventura)+
- **macOS**: 14+ (Sonoma)+

### Container Runtime Requirements

#### Docker Engine
- **Minimum Version**: 20.10.0
- **Recommended Version**: 24.0+
- **Features Required**: 
  - Docker Compose V2 support
  - Health check support
  - Resource limits support
  - Network isolation

#### Docker Compose
- **Minimum Version**: 2.0.0
- **Recommended Version**: 2.20+
- **Features Required**:
  - Service dependencies
  - Health checks
  - Resource limits
  - Environment variable substitution

### Additional Software

#### Python (for testing and CLI tools)
- **Minimum Version**: 3.8
- **Recommended Version**: 3.11+
- **Required Packages**: requests, aiohttp, python-dotenv

#### Git (for deployment)
- **Minimum Version**: 2.20+
- **Recommended Version**: 2.40+

## Network Requirements

### Bandwidth Requirements

#### Minimum Bandwidth
- **Internet**: 10 Mbps down, 5 Mbps up
- **Local Network**: 100 Mbps ethernet
- **Home Assistant**: Stable connection to HA instance

#### Recommended Bandwidth
- **Internet**: 25+ Mbps down, 10+ Mbps up
- **Local Network**: 1 Gbps ethernet
- **Home Assistant**: Low-latency connection

### Network Configuration

#### Port Requirements
```
External Ports (exposed to host):
├── 8086: InfluxDB web interface
├── 8001: WebSocket ingestion service
├── 8002: Enrichment pipeline service
├── 8003: Admin API service
├── 8080: Data retention service
└── 3000: Health dashboard

Internal Ports (container communication):
├── 8086: InfluxDB internal
├── 8001: WebSocket ingestion internal
├── 8002: Enrichment pipeline internal
├── 8004: Admin API internal
├── 8080: Data retention internal
└── 80: Health dashboard internal
```

#### Firewall Configuration
- **Inbound**: Allow ports 8086, 8001, 8002, 8003, 8080, 3000
- **Outbound**: Allow HTTPS (443) for weather API
- **Local**: Allow all internal container communication

### Connectivity Requirements

#### External Services
- **OpenWeatherMap API**: HTTPS access to api.openweathermap.org
- **Home Assistant**: HTTP/WebSocket access to HA instance
- **Docker Hub**: HTTPS access for image pulls

#### Internal Services
- **Container Network**: All services must communicate internally
- **Service Discovery**: DNS resolution between containers
- **Health Checks**: HTTP health check endpoints accessible

## Storage Requirements

### Storage Architecture

#### Volume Types
- **Database Data**: Persistent volume for InfluxDB
- **Configuration**: Persistent volume for InfluxDB config
- **Logs**: Persistent volumes for application logs
- **Backups**: Persistent volume for backup storage

#### Storage Layout
```
/var/lib/docker/volumes/
├── homeiq_influxdb_data/     # Database data
├── homeiq_influxdb_config/   # Database configuration
├── homeiq_websocket_logs/    # WebSocket service logs
├── homeiq_enrichment_logs/   # Enrichment service logs
├── homeiq_admin_logs/        # Admin API logs
├── homeiq_retention_logs/    # Data retention logs
└── homeiq_backups/           # Backup storage
```

### Storage Performance

#### Database Storage
- **Type**: SSD or NVMe SSD recommended
- **IOPS**: 1000+ IOPS for optimal performance
- **Latency**: < 1ms for database operations

#### Log Storage
- **Type**: Any storage type acceptable
- **Performance**: Lower performance requirements
- **Retention**: 30-day automatic rotation

#### Backup Storage
- **Type**: Network storage or external drives
- **Capacity**: 2x database size minimum
- **Performance**: Moderate performance requirements

## Platform Compatibility

### Hardware Platforms

#### x64 Architecture
- **Intel**: All modern Intel processors (2015+)
- **AMD**: All modern AMD processors (2015+)
- **Virtualization**: VMware, VirtualBox, Hyper-V, KVM

#### ARM64 Architecture
- **Apple Silicon**: M1, M2, M3 processors
- **Raspberry Pi**: Pi 4, Pi 5
- **ARM Servers**: AWS Graviton, Oracle ARM instances

#### Virtualization Platforms
- **VMware**: ESXi 6.5+, Workstation, Fusion
- **VirtualBox**: 6.0+
- **Hyper-V**: Windows 10/11, Windows Server
- **KVM**: Linux virtualization
- **Docker Desktop**: Windows, macOS, Linux

### Cloud Platforms

#### Supported Cloud Providers
- **AWS**: EC2, ECS, EKS
- **Google Cloud**: Compute Engine, GKE
- **Azure**: Virtual Machines, AKS
- **DigitalOcean**: Droplets
- **Linode**: Compute instances
- **Vultr**: Cloud instances

#### Container Platforms
- **Kubernetes**: 1.20+
- **Docker Swarm**: 20.10+
- **Nomad**: 1.0+
- **OpenShift**: 4.6+

## Performance Benchmarks

### Test Environment
- **Hardware**: Intel i5-8400, 16GB RAM, 500GB SSD
- **Software**: Ubuntu 22.04 LTS, Docker 24.0, Docker Compose 2.20
- **Network**: 1 Gbps ethernet

### Benchmark Results

#### Event Processing Performance
```
Events per minute:
├── 100 events/min: 5% CPU, 2GB RAM
├── 500 events/min: 15% CPU, 3GB RAM
├── 1000 events/min: 30% CPU, 4GB RAM
└── 2000 events/min: 60% CPU, 6GB RAM
```

#### Database Performance
```
InfluxDB Write Performance:
├── 10 writes/sec: 1ms latency
├── 50 writes/sec: 5ms latency
├── 100 writes/sec: 10ms latency
└── 500 writes/sec: 25ms latency
```

#### API Response Times
```
Admin API Response Times:
├── Health Check: 50ms average
├── Statistics: 100ms average
├── Configuration: 75ms average
└── Events Query: 200ms average
```

### Resource Utilization

#### CPU Usage by Service
```
Service CPU Usage (at 1000 events/min):
├── InfluxDB: 40%
├── WebSocket Ingestion: 25%
├── Enrichment Pipeline: 20%
├── Admin API: 10%
├── Data Retention: 3%
└── Health Dashboard: 2%
```

#### Memory Usage by Service
```
Service Memory Usage:
├── InfluxDB: 2.5GB
├── Enrichment Pipeline: 800MB
├── WebSocket Ingestion: 400MB
├── Admin API: 300MB
├── Data Retention: 200MB
└── Health Dashboard: 100MB
```

## Scaling Considerations

### Horizontal Scaling

#### Multi-Instance Deployment
- **Load Balancer**: Required for multiple instances
- **Database Clustering**: InfluxDB cluster for high availability
- **Session Management**: Stateless service design

#### Service Scaling
- **WebSocket Ingestion**: Scale based on event volume
- **Enrichment Pipeline**: Scale based on processing backlog
- **Admin API**: Scale based on concurrent users

### Vertical Scaling

#### Resource Increases
- **CPU**: Linear performance improvement up to 8 cores
- **Memory**: Improved caching and reduced swapping
- **Storage**: Better I/O performance with faster storage

#### Performance Optimization
- **Database Tuning**: InfluxDB configuration optimization
- **Network Optimization**: Faster network interfaces
- **Container Optimization**: Resource limit tuning

### Capacity Planning

#### Growth Projections
- **Year 1**: 1M events, 10GB storage
- **Year 2**: 5M events, 50GB storage
- **Year 3**: 10M events, 100GB storage

#### Scaling Triggers
- **CPU Usage**: > 70% sustained
- **Memory Usage**: > 80% sustained
- **Storage Usage**: > 80% capacity
- **Response Time**: > 2x baseline

---

**Last Updated**: 2024-12-19  
**Version**: 1.0.0
