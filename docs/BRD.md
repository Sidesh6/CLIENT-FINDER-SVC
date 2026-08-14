# Business Requirements Document

## 1. Project Name

Client Finder

## 2. Problem Statement

Finding legitimate public project opportunities online is time-consuming.

A developer may need to search multiple platforms, read large numbers of project descriptions, determine whether a project is relevant, identify required skills, check budget information, and decide whether the opportunity is worth pursuing.

The system aims to automate this discovery and analysis process.

## 3. Business Objective

Build an AI-powered platform that discovers public project opportunities and ranks them according to their relevance and potential value.

## 4. Target User

Primary user:

- Freelancers
- Independent developers
- AI developers
- Software development agencies
- Small development teams

## 5. Core Requirements

### Project Discovery

The system shall collect publicly available project opportunities from supported sources.

### Data Extraction

The system shall extract:

- Project title
- Project description
- Required skills
- Budget
- Currency
- Project type
- Client information when publicly available
- Deadline
- Source
- Source URL
- Posting date

### Data Cleaning

The system shall:

- Remove unnecessary whitespace
- Normalize text
- Validate required fields
- Detect duplicate projects

### AI Analysis

The system shall analyze project descriptions and identify:

- Required technologies
- Project category
- Estimated complexity
- Relevant skills
- Potential fit
- Project quality

### Project Scoring

The system shall calculate a project opportunity score.

Example:

```text
Opportunity Score =
    Relevance
    + Budget
    + Skill Match
    + Project Quality
    + Client Quality
    + Freshness