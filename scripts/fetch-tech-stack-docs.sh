#!/bin/bash
# Fetch missing Context7 documentation for tech stack
# Run with: @bmad-master and execute each command

echo "Fetching missing Context7 documentation for tech stack..."
echo "Run these commands with @bmad-master:"
echo ""

echo "# Critical Stack - SQLAlchemy"
echo "*context7-docs sqlalchemy async-orm"
echo "*context7-docs sqlalchemy 2.0-migration"
echo "*context7-docs sqlalchemy fastapi-integration"
echo ""

echo "# Critical Stack - Pydantic"
echo "*context7-docs pydantic v2-migration"
echo "*context7-docs pydantic fastapi-integration"
echo "*context7-docs pydantic settings"
echo ""

echo "# Critical Stack - aiosqlite"
echo "*context7-docs aiosqlite async-patterns"
echo "*context7-docs aiosqlite sqlalchemy-integration"
echo ""

echo "# Critical Stack - Zustand"
echo "*context7-docs zustand state-management"
echo "*context7-docs zustand react-integration"
echo ""

echo "# AI/ML Stack - PyTorch"
echo "*context7-docs pytorch cpu-only"
echo "*context7-docs pytorch optimization"
echo ""

echo "# AI/ML Stack - PEFT"
echo "*context7-docs peft lora"
echo "*context7-docs peft fine-tuning"
echo ""

echo "# AI/ML Stack - LangChain"
echo "*context7-docs langchain llm-orchestration"
echo "*context7-docs langchain openai-integration"
echo ""

echo "# AI/ML Stack - OpenVINO"
echo "*context7-docs openvino int8-optimization"
echo "*context7-docs openvino model-export"
echo ""

echo "# AI/ML Stack - optimum-intel"
echo "*context7-docs optimum-intel transformers-integration"
echo "*context7-docs optimum-intel openvino-export"
echo ""

echo "After fetching, verify with:"
echo "*context7-kb-status"

