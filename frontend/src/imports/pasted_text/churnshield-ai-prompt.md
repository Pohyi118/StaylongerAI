# CHURNSHIELD AI — FINAL PRODUCT BUILD PROMPT

Build a production-quality, mobile-first B2B SaaS application called **ChurnShield AI**.

Tagline:

**Smart Retention System**

This is NOT a generic analytics dashboard.

It is an **AI-powered autonomous revenue protection system for B2B SaaS companies** that detects silent churn before cancellation, identifies which customers are actually worth saving, chooses the best retention intervention, and autonomously executes micro-rewards using Solana + x402 when appropriate.

The entire product should feel like a premium startup product that could realistically be presented by a funded fintech / AI SaaS company.

---

# 1. CORE PRODUCT CONCEPT

B2B SaaS companies lose customers because customer information is fragmented across:

* Billing systems
* Product usage
* Login activity
* Feature clicks
* Support tickets
* Customer complaints
* Subscription information

By the time a Customer Success Manager realizes that an SME customer has stopped using the platform, that customer may already have psychologically decided to cancel.

ChurnShield AI continuously combines this information and creates a real-time **Customer Health Score**.

The AI then predicts churn risk and classifies customers according to whether intervention is economically worthwhile.

The system should NOT blindly give discounts to everybody.

Its key philosophy is:

> Save the customers worth saving, avoid wasting retention budget on customers who do not need intervention, and escalate only high-value cases to humans.

---

# 2. THE 90/10 OPERATING MODEL

This is one of the most important concepts of the entire application.

### Top 10% — VIP Accounts

High-value accounts with significant MRR or strategic importance.

AI detects the problem but does NOT automatically make major decisions.

Instead:

**AI Detection → AI Diagnosis → Human Alert → Customer Success Manager Decision**

Display these as:

**Top 10% VIPs**
High-value accounts
Status: **Human Alert**

---

### Bottom 90% — SME Accounts

Lower-value accounts that would be too expensive for Customer Success Managers to manually monitor individually.

These accounts are handled autonomously by ChurnShield AI.

Flow:

**AI Detection → Diagnosis → Select Intervention → Execute → Monitor Result → Learn**

Display:

**Bottom 90% SMEs**
AI-handled automatically
Status: **AI Handled**

The 90/10 model must be visually prominent inside the dashboard.

---

# 3. CUSTOMER SEGMENTATION

Under the Bottom 90% SME section, classify customers into four behavioral quadrants.

## Persuadables

Icon:
Target / bullseye

Color:
Soft coral / pink

Meaning:
High churn risk but still recoverable.

Subtitle:

**High risk, can be saved**

AI Action:

**Invest Rewards**

These customers should receive personalized retention interventions.

---

## Sure Things

Icon:
Heart / shield-heart

Color:
Mint green

Meaning:
Healthy, loyal and actively engaged.

Subtitle:

**Loyal & engaged**

AI Action:

**No Discount**

The system deliberately avoids wasting retention budget on them.

---

## Inactive

IMPORTANT:

Do NOT use the term "Sleeping Dogs".

Use:

**Inactive**

Icon:
Pause / idle activity icon

Color:
Soft amber / warm yellow

Subtitle:

**Low activity, monitor quietly**

AI Action:

**Monitor**

The AI should avoid unnecessary intervention because contacting these users could remind them about a subscription they were otherwise continuing to pay for.

---

## Lost Causes

Icon:
Trash / archive / faded user

Color:
Neutral grey / desaturated lavender

Subtitle:

**Unlikely to stay**

AI Action:

**Ignore**

The system avoids wasting retention budget on customers with extremely low recovery probability.

---

# 4. CUSTOMER HEALTH ENGINE

Create an AI Customer Health Score using mock data from:

* Login frequency
* Days since last login
* Feature usage
* Product adoption
* Subscription value
* Payment history
* Support tickets
* Complaints
* Usage trend
* Team activity
* Historical churn patterns

Example:

Health Score: **42 / 100**

Churn Probability: **78%**

MRR at Risk: **RM12,460**

Customer Segment:

**Persuadable**

AI should also provide a short natural-language explanation:

"Product usage dropped 41% over the last 14 days and the team stopped using Automation Builder, previously their most frequently used feature."

---

# 5. MARKET ANOMALY / COMPETITOR ALERT

Create an important dashboard component called:

**COMPETITOR ALERT**

This card should visually resemble a high-priority AI detection system.

Example:

**Sudden drop in user activity detected.
Possible competitor move.**

Emergency badge:

**EMERGENCY**

Display:

Activity Drop
**-37%**

Affected Users
**2,391**

Time Detected
**09:41 AM**

CTA:

**Notify Executive Team**

Use a coral-red diffuse glow, but keep it elegant rather than aggressive.

Include a subtle radar / anomaly visualization.

The card should feel like an AI early-warning system rather than a normal notification.

---

# 6. REVENUE COMMAND CENTER

The main dashboard is the executive control center.

Show major metrics such as:

### Revenue Protected

**RM184,320**

### Accounts Rescued

**47**

### Intervention ROI

**8.4×**

### MRR at Risk

**RM24,500**

### Persuadables

**45**

### Sure Things

**1,204**

### Inactive

**89**

### Lost Causes

**12**

Include a smooth revenue-protected line chart.

The chart should show approximately the last 30 days.

Use an elegant purple → pink → orange gradient line with a very soft translucent glow underneath.

Avoid generic admin-dashboard styling.

---

# 7. AI EXECUTIVE BRIEF

Create a premium card titled:

**AI Executive Brief**

Example copy:

"Churn exposure decreased 12% this week.
9 persuadable accounts were automatically rescued.
A coordinated activity drop across 127 SME customers may indicate a competitor campaign."

CTA:

**View Analysis**

This should feel like having an AI Chief Revenue Officer summarizing the company.

---

# 8. RESCUE AGENT

This is the core feature of the product.

When ChurnShield identifies a Persuadable account, create a Rescue Case.

Example:

Customer:

**Acme Corp**

MRR:

**RM12,460**

Health Score:

**38**

Churn Risk:

**82%**

Primary Problem:

**Feature underutilization**

AI Diagnosis:

"The customer continues paying for the Growth plan but has stopped using Workflow Automation, which previously generated most of their platform value."

Recommended Intervention:

**Convert unused value into Value Vault credits**

Predicted Save Probability:

**74%**

Estimated Intervention Cost:

**RM50**

Revenue Protected:

**RM12,460**

Expected ROI:

**249×**

Provide actions:

**Approve Rescue**

**Modify Strategy**

**Contact Customer**

For Bottom 90% accounts, show:

**Auto Rescue Enabled**

---

# 9. VALUE VAULT

Do NOT rely on generic percentage discounts.

This is one of the project's main differentiators.

Create:

**Value Vault**

If the customer pays for features they are not currently using, ChurnShield converts part of that unused value into flexible retention credits.

The customer may choose between interventions such as:

* Pause subscription temporarily
* Product credit
* Feature upgrade
* Relevant service reward
* Partner voucher
* Personalized business benefit

Example:

**RM50 Value Vault Credit Available**

Instead of:

"Here is a random 20% discount."

ChurnShield should communicate:

"We noticed you're not getting full value from your current plan. We've protected RM50 of your unused value. Choose how you'd like to use it."

This should feel personalized and economically rational.

---

# 10. CUSTOMER RESCUE EXPERIENCE

Create a customer-facing mobile page accessible from WhatsApp without requiring the customer to create a crypto wallet.

Example message:

**We noticed you haven't been getting the full value from your subscription.**

**RM50 of value has been protected for you.**

Choose:

### Pause My Subscription

or

### Use My RM50 Reward

If reward is selected, display available personalized rewards.

Example:

**GrabFood RM50**

Button:

**Claim Reward**

After successful claim:

**Reward unlocked ✓**

The customer should NEVER need to understand blockchain.

No seed phrase.

No wallet setup.

No crypto terminology.

No gas fees.

No technical Solana terminology.

Blockchain must remain invisible in the customer UX.

---

# 11. SOLANA + x402 BACKEND LOGIC

Solana should solve a real infrastructure problem rather than being included as decoration.

When the Rescue Agent determines that a customer should receive a reward:

1. AI selects the intervention.
2. AI requests the reward from a partner API.
3. Partner API responds with:

**HTTP 402 — Payment Required**

4. ChurnShield's AI Agent Wallet autonomously pays the required amount.
5. Payment happens using **USDC on Solana**.
6. Transaction confirmation occurs rapidly with very low transaction cost.
7. Partner API releases the voucher / barcode / reward.
8. ChurnShield sends it to the customer through WhatsApp.
9. Customer sees only the reward.

Represent this inside the admin dashboard as:

**Agent Payment**

Status:
**Executed**

Settlement:
**USDC**

Network:
**Solana**

Protocol:
**x402**

Transaction:
shortened transaction ID

Do NOT expose this information in the consumer interface.

---

# 12. RESCUE TIMELINE

Inside every rescued customer account, create a chronological AI activity timeline.

Example:

**09:31**
Activity anomaly detected

**09:32**
Churn probability increased from 41% → 78%

**09:33**
Account classified as Persuadable

**09:34**
Unused subscription value identified

**09:35**
RM50 Value Vault intervention selected

**09:35**
x402 payment executed via Solana

**09:36**
WhatsApp rescue message delivered

**10:08**
Customer claimed reward

**10:24**
Customer returned to platform

**11:15**
Churn probability decreased to 32%

Final badge:

**RESCUED**

This timeline should make the autonomous AI-agent behavior extremely obvious during the hackathon demo.

---

# 13. VIP ATTENTION

Create a dedicated section:

**VIP Attention Required**

Each VIP card should show:

Company name

Industry

Revenue at risk

Health Score

Churn probability

Detected issue

Last activity

Example:

**Acme Corp**

Enterprise

Revenue at Risk:
**RM12,460**

Health:
**31 / 100**

Churn Risk:
**87%**

CTA:

**Assign CSM**

Secondary CTA:

**Call Now**

VIP accounts must visually use:

**Human Decision Required**

Do NOT automatically issue rewards to these accounts.

---

# 14. CUSTOMER DETAIL PAGE

When a customer is opened, display:

Customer name

Plan

MRR

Health Score

Churn Probability

Segment

Last Active

Account Owner

Usage Trend

Feature Adoption

Support Sentiment

Payment Status

MRR at Risk

Then create:

### AI Diagnosis

### Recommended Intervention

### Rescue Timeline

### Value Vault

### Engagement History

### AI Decision Explanation

Avoid giant data tables.

Use visual cards, compact charts and progressive disclosure.

---

# 15. REVERSE ONBOARDING

Include an experimental feature called:

**AI Quick Onboarding**

Some Malaysian SME businesses still operate using spreadsheets, WhatsApp or handwritten records.

Allow an SME operator to upload:

* Screenshot
* Spreadsheet
* Invoice
* Handwritten record
* Inventory image

Vision AI extracts the information automatically and structures it into the ChurnShield system.

Example:

**Upload your existing customer records**

AI response:

**127 customers detected**

**RM48,240 recurring revenue identified**

**18 accounts require immediate analysis**

CTA:

**Import Customers**

This reduces setup friction.

---

# 16. MAIN NAVIGATION

Use a premium floating bottom navigation.

Tabs:

### Dashboard

Home icon

### Customers

Users icon

### Alerts

Bell / radar icon

### Rewards

Gift / Value Vault icon

### Reports

Analytics icon

Keep navigation minimal.

The active tab should use a glowing translucent capsule.

---

# 17. REQUIRED SCREENS

Build the experience as a real multi-page product.

Required screens:

1. Dashboard / Revenue Command Center
2. Competitor Alert Detail
3. Customers
4. Customer Detail
5. VIP Attention
6. Rescue Agent Case
7. Value Vault
8. Rewards / Agent Transactions
9. Alerts
10. Reports / Revenue Protected Analytics
11. AI Quick Onboarding
12. Customer-facing Rescue Page
13. Settings / Integrations

Do NOT make every feature exist on one giant dashboard.

The dashboard is a summary.

Detailed information belongs in secondary screens.

---

# 18. VISUAL DIRECTION — CRITICAL

Follow this EXACT overall aesthetic:

**Premium Diffuse Gradient UI / 弥散风格**

The UI should combine:

* futuristic AI product
* premium fintech application
* soft glassmorphism
* diffuse ambient gradients
* subtle aurora lighting
* editorial typography
* extremely clean SaaS usability

The application should look like something showcased on:

* Mobbin
* Linear
* Raycast
* Arc
* Stripe
* modern award-winning fintech apps

It must NOT look like a default AI-generated dashboard.

---

# 19. COLOR SYSTEM

Base background:

warm off-white / extremely pale lavender.

Use large blurred ambient gradient areas rather than obvious rectangular gradients.

Primary ambient colors:

* Lavender
* Periwinkle
* Ice blue
* Soft pink
* Peach
* Very subtle mint

Primary brand accent:

**Electric violet / lavender**

Warning:

**Coral red → pink**

Success:

**Emerald / mint**

Inactive:

**Warm amber**

Neutral:

**Blue-grey / lavender-grey**

The colors should appear to softly diffuse into each other.

Do NOT oversaturate the page.

Approximately 75–80% of the interface should remain white / near-white.

---

# 20. DIFFUSE LIGHT EFFECT

Place extremely soft blurred gradient glows behind important areas.

Examples:

Competitor Alert:
coral + pink diffusion

AI Insight:
lavender + pink + blue diffusion

Value Vault:
peach + gold diffusion

Success:
mint + cyan diffusion

These gradients should behave like ambient lighting behind translucent glass.

Avoid obvious gradient rectangles.

Avoid neon cyberpunk styling.

Avoid excessive purple everywhere.

---

# 21. CARD DESIGN

Cards should have:

* 22–28px border radius
* translucent white surface
* extremely subtle border
* low-opacity glass effect
* soft ambient shadow
* generous padding
* strong visual hierarchy

Important cards may have subtle colored glow behind them.

Cards should visually float but remain restrained.

Avoid:

* thick borders
* excessive shadows
* dark outlines
* tiny cramped cards
* bootstrap-style components

---

# 22. TYPOGRAPHY

Use:

**Geist**

Preferred fallback:

Inter / Satoshi-like modern sans-serif.

Typography should feel editorial and modern.

Headings:

strong but not excessively bold.

Recommended hierarchy:

Hero metric:
48–56px

Page title:
28–32px

Section heading:
20–24px

Card heading:
16–18px

Body:
14–16px

Metadata:
12–13px

Use dark navy / near-black instead of pure black.

Numbers must use tabular numerals where appropriate.

Important financial numbers should have significant visual emphasis.

---

# 23. ICONOGRAPHY

Use clean outline icons.

Preferred:

**Lucide Icons**

Do NOT use random emoji as interface icons.

Use small circular translucent icon containers with subtle colored backgrounds.

Examples:

Persuadables → Target

Sure Things → Heart

Inactive → PauseCircle / Activity

Lost Causes → Archive / Trash2

VIP → Crown

AI → Sparkles

Alerts → Radar

Revenue → TrendingUp

Value Vault → Gift

Customers → Users

---

# 24. MOTION

Add premium micro-interactions.

Examples:

Cards gently lift on hover.

Buttons compress slightly when tapped.

Numbers animate when dashboard loads.

Charts animate from left to right.

Alerts pulse subtly.

AI processing displays soft orbiting particles.

Rescue timeline events appear sequentially.

Value Vault reward unlock uses a small glow animation.

Navigation indicator slides smoothly between tabs.

Animations should be subtle and fast.

Do NOT make the interface feel like a gaming application.

---

# 25. DASHBOARD HIERARCHY

The Dashboard should approximately follow this order:

Header

↓

AI protection status

↓

Revenue Protected hero card

↓

AI Executive Brief

↓

Key metrics

↓

Competitor / Market Anomaly Alert

↓

90/10 Split

↓

SME Quadrants

↓

VIP Attention Required

↓

Recent AI Rescues

↓

Floating Bottom Navigation

Do NOT make every component equally visually strong.

Hierarchy is critical.

The eye should first see:

**Revenue Protected**

then:

**AI Insight / Urgent Alert**

then:

**Customer actions**

---

# 26. DESKTOP EXPERIENCE

Although the primary design language is mobile-first, create a premium responsive desktop version.

Desktop should NOT simply stretch the mobile layout.

Use:

* side navigation
* wider analytics areas
* 12-column grid
* larger charts
* split-panel customer details
* sticky AI action panel
* spacious max-width container

Maintain exactly the same diffuse visual language.

---

# 27. INTERACTIONS

This must NOT be a static design mockup.

All important buttons must work.

Examples:

Click Customers → customer list

Click VIP → VIP page

Click Alert → alert details

Click Persuadables → filtered customer list

Click customer → detail page

Click Rescue → Rescue Agent case

Click Value Vault → available interventions

Click Reward → reward execution

Click Reports → analytics

Click dashboard chart period → change period

Click AI Executive Brief → full explanation

Click notification → relevant case

Buttons should provide realistic loading, success and error states.

---

# 28. DEMO DATA

Populate the application with realistic Malaysian B2B SaaS demo data.

Currency:

**RM / MYR**

Example companies:

Acme Corp
Nexora Solutions
Kinetic Labs
OrbitWorks
Vertex Systems
Lumina Tech
ScaleForge
Maju Digital

Avoid lorem ipsum.

Use realistic business language.

---

# 29. TECHNICAL IMPLEMENTATION

Preferred frontend:

* Next.js
* TypeScript
* Tailwind CSS
* shadcn/ui
* Lucide Icons

Use reusable components.

Create a proper design system.

Do not hard-code every section individually.

Suggested reusable components:

DashboardCard

MetricCard

CustomerHealthBadge

SegmentBadge

GlassPanel

DiffuseGlow

AlertCard

AIInsightCard

RescueTimeline

CustomerCard

RewardCard

AgentTransaction

HealthScore

RiskBadge

RevenueChart

BottomNavigation

Use clean component architecture.

---

# 30. PRODUCT STORY THE UI MUST COMMUNICATE

A judge should understand this story within approximately 30 seconds:

**1. ChurnShield detects silent customer churn before cancellation.**

↓

**2. It identifies which customers are actually worth saving.**

↓

**3. VIP customers receive human attention.**

↓

**4. The remaining 90% are handled autonomously by AI.**

↓

**5. Persuadable customers receive personalized interventions instead of blanket discounts.**

↓

**6. Unused subscription value becomes Value Vault credits.**

↓

**7. AI can autonomously purchase rewards through x402 + USDC on Solana.**

↓

**8. The customer never needs to know blockchain is involved.**

↓

**9. ChurnShield measures whether the intervention actually worked.**

↓

**10. The company sees measurable REVENUE PROTECTED rather than meaningless AI predictions.**

This story is more important than adding random features.

---

# 31. FINAL DESIGN RULES

DO NOT:

* create a generic admin dashboard
* use excessive purple gradients
* use cartoon illustrations
* use emoji as product icons
* overcrowd the interface
* make every card glow
* overuse glassmorphism
* use giant meaningless charts
* create random features outside the product concept
* turn Solana into the visual focus
* expose crypto complexity to customers
* use "Sleeping Dogs"
* use blanket discount logic
* make the interface look like a hackathon prototype

DO:

* use **Inactive**
* preserve the 90/10 model
* emphasize Revenue Protected
* make autonomous AI behavior visible
* demonstrate AI reasoning
* demonstrate Value Vault
* demonstrate x402 agent payment
* distinguish Human vs AI decisions
* maintain strong information hierarchy
* use restrained diffuse gradient lighting
* create realistic interactions
* make every screen presentation-ready

---

# FINAL GOAL

The finished product should feel like:

**Stripe × Linear × premium fintech × autonomous AI agent**

with a subtle futuristic diffuse-gradient aesthetic.

It should look polished enough that a judge initially assumes it is an existing funded SaaS startup rather than a hackathon prototype.

Do not redesign the concept.

Do not simplify the business logic.

Do not remove the 90/10 system, SME quadrants, Value Vault, Rescue Agent, VIP escalation, anomaly detection, Solana or x402.

Improve the visual execution, hierarchy, transitions and usability while preserving the complete ChurnShield AI product concept.

Build the application now.
