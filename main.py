Create a complete, production-ready Telegram bot called “AVOID REPORTS” for my Telegram channel @avoidrep.

The bot is a community scam-report submission and moderation system. Users can submit reports about accounts involved in alleged scams. No report should be automatically published. Every report must first go to a private admin review chat, and only an admin can approve or reject it.

Use a clean, professional, premium-looking Telegram UI with inline buttons, emojis, clear formatting, Back buttons, Cancel buttons, and proper error handling.

IMPORTANT CONFIGURATION:
- Public Channel: @avoidrep
- Use environment variables for BOT_TOKEN, ADMIN_IDS, ADMIN_CHAT_ID, and CHANNEL_USERNAME.
- Never hardcode the bot token.
- The bot must use persistent database storage so reports remain saved after restart.
- Generate unique report IDs in this format: #AVD0001, #AVD0002, #AVD0003, etc.
- Escape all user-generated text before displaying it with HTML parse mode.
- Only configured admins can approve, reject, ban users, broadcast, or access the admin panel.

==================================================
1. START COMMAND
==================================================

When a user sends /start, show:

🛡️ WELCOME TO AVOID REPORTS

A community-driven reporting platform designed to help users submit and review reports related to potentially fraudulent deals.

📋 Every report is manually reviewed by our moderation team before publication.

⚠️ False, incomplete, misleading, or manipulated reports may be rejected.

Choose an option below to continue.

🛡️ Powered by @avoidrep

Buttons:

🚨 Report a Scammer
🔍 Search Reports
📋 My Reports
📜 Reporting Guidelines
📢 Join @avoidrep

The “Join @avoidrep” button must open:
https://t.me/avoidrep

==================================================
2. REPORT A SCAMMER
==================================================

When the user presses:

🚨 Report a Scammer

Show:

🚨 CREATE A NEW REPORT

Please select the platform where the incident occurred.

Buttons:

✈️ Telegram
📸 Instagram
🌐 Other
❌ Cancel

Save the selected platform and continue.

==================================================
3. ACCUSED USER INFORMATION
==================================================

Show:

👤 REPORTED ACCOUNT INFORMATION

Please send the username of the account you want to report.

Examples:

@username

For Telegram reports, you may also send a numeric Telegram User ID if the account does not have a username.

Example:

123456789

⚠️ Please make sure you are reporting the correct account.

Validate the input.

For a username:
- Accept @username
- Store the username without duplicate @ symbols
- Preserve the original username for display

For numeric IDs:
- Accept numeric Telegram User IDs

Then continue.

==================================================
4. DEAL VALUE
==================================================

Show:

💰 DEAL VALUE

Enter the total amount involved in the deal.

Examples:

$100
₹5,000
100 USDT

If no money was involved, send:

0

Save the value and continue.

==================================================
5. INCIDENT DESCRIPTION
==================================================

Show:

📝 INCIDENT DETAILS

Briefly explain what happened.

Please include:

• What the deal was for
• What you paid, sent, or provided
• What the other party agreed to do
• What went wrong

Keep your explanation clear, factual, and concise.

Minimum description length: 20 characters.
Maximum description length: 3000 characters.

Save the description and continue.

==================================================
6. EVIDENCE SUBMISSION
==================================================

Show:

📂 SUBMIT EVIDENCE

Create a Telegram channel containing all relevant evidence and send the channel link here.

Your evidence channel should preferably include:

• Full conversation screenshots
• Screen recording of the conversation
• Reported account's profile
• Username and User ID, if available
• Payment or transaction proof
• Any other relevant evidence

Public or private Telegram channel invite links are accepted.

Example:

https://t.me/+xxxxxxxx

⚠️ Incomplete, misleading, or manipulated evidence may result in the report being rejected.

Only accept valid Telegram links beginning with:
https://t.me/

Save the evidence link and continue.

==================================================
7. REVIEW REPORT BEFORE SUBMISSION
==================================================

Show a complete preview:

🔎 REVIEW YOUR REPORT

━━━━━━━━━━━━━━━━━━

🚨 REPORT DETAILS

📱 Platform: {platform}
👤 Reported Account: {username_or_user_id}
💰 Deal Value: {deal_value}

📝 Incident Details:

{description}

📂 Evidence:

{evidence_link}

━━━━━━━━━━━━━━━━━━

⚠️ By submitting this report, you confirm that the information and evidence provided are accurate to the best of your knowledge.

Buttons:

✅ Submit Report
✏️ Edit Report
🔄 Start Again
❌ Cancel

The Edit Report button should show:

✏️ EDIT REPORT

Choose what you want to edit:

📱 Platform
👤 Reported Account
💰 Deal Value
📝 Description
📂 Evidence
⬅️ Back to Preview

After editing any field, return to the report preview.

==================================================
8. SUBMIT REPORT
==================================================

When the user presses:

✅ Submit Report

Create a unique report ID.

Example:

#AVD0001

Save all information to the database.

Show the user:

✅ REPORT SUBMITTED SUCCESSFULLY

Your report has been sent to the AVOID REPORTS moderation team for manual review.

🆔 Report ID: #AVD0001
⏳ Status: Pending Review

You will receive an update when your report is:

✅ Approved
❌ Rejected
📩 Returned for Additional Evidence

You can check the status of your report at any time from “My Reports”.

⚠️ False reports or manipulated evidence may result in reporting restrictions.

🛡️ @avoidrep

Buttons:

📋 My Reports
🏠 Main Menu

==================================================
9. SEND NEW REPORT TO PRIVATE ADMIN CHAT
==================================================

Immediately send the complete report to ADMIN_CHAT_ID.

Admin message:

🚨 NEW REPORT RECEIVED

━━━━━━━━━━━━━━━━━━

🆔 Report ID: #AVD0001
⏳ Status: PENDING REVIEW

👤 REPORTER

Username: @reporter
User ID: 123456789

🚨 REPORTED ACCOUNT

Platform: Telegram
Username: @username
User ID: 987654321

💰 DEAL VALUE

$100

📝 INCIDENT DETAILS

{description}

📂 EVIDENCE

{evidence_link}

━━━━━━━━━━━━━━━━━━

Submitted: {date_and_time}

Admin buttons:

✅ Approve
❌ Reject
📩 Request More Proof
👤 View Reporter
📂 Open Evidence
🚫 Ban Reporter

If the reported Telegram account has a valid username, also show:

👤 View Reported User

==================================================
10. APPROVE REPORT
==================================================

Only configured admins can use the Approve button.

Before final approval, show:

⚠️ CONFIRM APPROVAL

Are you sure you want to approve and publish report #AVD0001 to @avoidrep?

Buttons:

✅ Confirm & Publish
❌ Cancel

When confirmed:

- Change report status to APPROVED.
- Save the reviewing admin ID.
- Save review date and time.
- Automatically publish the report to @avoidrep.
- Save the published channel message ID.
- Notify the reporter.

Reporter notification:

✅ YOUR REPORT HAS BEEN APPROVED

🆔 Report ID: #AVD0001

Your report has been reviewed and approved by the AVOID REPORTS moderation team.

The report has now been published to @avoidrep.

Thank you for helping the community review potential risks.

Buttons:

📢 View Published Report
🏠 Main Menu

==================================================
11. PUBLIC CHANNEL POST
==================================================

Publish approved reports to @avoidrep using this format:

🚨 COMMUNITY SAFETY REPORT

━━━━━━━━━━━━━━━━━━

🆔 REPORT ID
#AVD0001

👤 REPORTED ACCOUNT
@username

🆔 USER ID
987654321

📱 PLATFORM
Telegram

💰 REPORTED DEAL VALUE
$100

📝 INCIDENT SUMMARY

{description}

📂 EVIDENCE

Supporting evidence is available through the button below.

━━━━━━━━━━━━━━━━━━

⚠️ This post records a community-submitted report reviewed by the moderation team based on the evidence provided. Users should review the available evidence and make their own assessment before dealing.

🛡️ AVOID REPORTS
@avoidrep

Buttons:

👤 View Profile
📂 View Evidence

The View Profile button should only appear when a valid profile URL can be created.

The View Evidence button should open the submitted evidence link.

==================================================
12. REJECT REPORT
==================================================

When an admin presses:

❌ Reject

Show rejection reasons:

📂 Insufficient Evidence
🧩 Incomplete Proof
🚫 Invalid Evidence
🔍 Unable to Verify
⚠️ Misleading Information
✍️ Custom Reason
⬅️ Back

If “Custom Reason” is selected, ask the admin to type the rejection reason.

After selecting a reason, show:

⚠️ CONFIRM REJECTION

Report: #AVD0001

Reason:
{rejection_reason}

Are you sure you want to reject this report?

Buttons:

❌ Confirm Rejection
⬅️ Back

After confirmation:

- Change status to REJECTED.
- Save the rejection reason.
- Save admin ID.
- Save review date and time.
- Notify the reporter.

Reporter notification:

❌ REPORT REJECTED

🆔 Report ID: #AVD0001

Your report was reviewed but could not be approved.

Reason:

{rejection_reason}

You may submit a new report if you can provide complete and verifiable information or evidence.

🛡️ @avoidrep

Buttons:

🚨 Submit New Report
🏠 Main Menu

==================================================
13. REQUEST MORE PROOF
==================================================

When an admin presses:

📩 Request More Proof

Ask the admin:

📩 REQUEST ADDITIONAL EVIDENCE

Please enter a short message explaining what additional evidence is required.

Example:

Please provide a full screen recording of the conversation and payment proof.

After the admin submits the request:

- Change report status to MORE PROOF REQUIRED.
- Save the admin request.
- Notify the reporter.

Reporter message:

📩 ADDITIONAL EVIDENCE REQUIRED

🆔 Report ID: #AVD0001

The moderation team requires additional evidence before a final decision can be made.

Moderator Request:

{admin_request}

Please submit the requested evidence below.

Button:

📂 Submit Additional Evidence

When the user presses the button:

Ask them to send a new or updated Telegram evidence channel link.

After receiving a valid link:

- Update the evidence link.
- Change status back to PENDING REVIEW.
- Send the updated report back to the admin review chat.
- Notify the user.

User confirmation:

✅ ADDITIONAL EVIDENCE SUBMITTED

🆔 Report ID: #AVD0001

Your updated evidence has been submitted to the moderation team.

⏳ Status: Pending Review

==================================================
14. SEARCH REPORTS
==================================================

When the user presses:

🔍 Search Reports

Show:

🔍 SEARCH REPORTS

Send an exact username or numeric User ID.

Examples:

@username
123456789

The bot will search approved reports in the AVOID REPORTS database.

If no approved report is found:

✅ NO APPROVED REPORT FOUND

No approved report was found for this username or User ID in the AVOID REPORTS database.

⚠️ This does not guarantee that an account is trustworthy. Always verify independently before making a deal.

Buttons:

🔍 Search Again
🏠 Main Menu

If approved reports are found:

🚨 APPROVED REPORTS FOUND

👤 Account: @username
📊 Approved Reports: 2

Recent Report IDs:

#AVD0001
#AVD0042

⚠️ Review the available reports and evidence before making your own decision.

Buttons:

📋 View Reports
🔍 Search Again
🏠 Main Menu

When “View Reports” is pressed, allow the user to browse approved reports one by one with:

⬅️ Previous
➡️ Next
📂 View Evidence
🏠 Main Menu

==================================================
15. MY REPORTS
==================================================

When the user presses:

📋 My Reports

Show only reports submitted by that Telegram user.

Example:

📋 MY REPORTS

1. #AVD0001
Status: ✅ Approved

2. #AVD0002
Status: ⏳ Pending Review

3. #AVD0003
Status: ❌ Rejected

Buttons should allow the user to open a specific report.

Report details:

📋 REPORT DETAILS

🆔 Report ID: #AVD0001
📱 Platform: Telegram
👤 Reported Account: @username
💰 Deal Value: $100
📅 Submitted: {date}
✅ Status: Approved

If rejected, also show:

❌ Rejection Reason:
{reason}

If more proof is required, show:

📩 Moderator Request:
{request}

==================================================
16. DUPLICATE REPORT DETECTION
==================================================

Before submitting a report, check whether the same username or User ID already has approved reports.

If approved reports already exist, show:

⚠️ EXISTING REPORT FOUND

This account already has approved reports in the AVOID REPORTS database.

👤 Account: @username
📊 Existing Approved Reports: 2

You may still submit a new report if your case involves a separate incident.

Buttons:

✅ Continue New Report
📋 View Existing Reports
❌ Cancel

Do not automatically block legitimate separate reports.

==================================================
17. ADMIN PANEL
==================================================

Command:

/admin

Only ADMIN_IDS can access it.

Show:

🛡️ AVOID REPORTS — ADMIN PANEL

Choose an option below.

Buttons:

📊 Statistics
⏳ Pending Reports
📩 More Proof Required
✅ Approved Reports
❌ Rejected Reports
🔍 Search Database
🚫 Banned Reporters
📢 Broadcast
📜 Admin Logs

==================================================
18. ADMIN STATISTICS
==================================================

Show:

📊 AVOID REPORTS STATISTICS

👥 Total Bot Users: {count}

📋 Total Reports: {count}
⏳ Pending: {count}
📩 More Proof Required: {count}
✅ Approved: {count}
❌ Rejected: {count}

🚨 Unique Reported Accounts: {count}
🚫 Banned Reporters: {count}

📅 Reports Today: {count}
📅 Approved Today: {count}

==================================================
19. ADMIN PENDING REPORTS
==================================================

Show pending reports with pagination.

Each item should display:

🆔 #AVD0001
👤 @username
💰 $100
📅 {date}

Buttons:

👁 Open Report
⬅️ Previous
➡️ Next
🏠 Admin Panel

==================================================
20. BAN / UNBAN REPORTER
==================================================

Admin commands:

/ban USER_ID
/unban USER_ID

When banned:

- User can still use the bot to view/search public reports.
- User cannot submit new reports.
- User cannot submit additional evidence.
- Show:

🚫 REPORTING ACCESS RESTRICTED

Your account is currently restricted from submitting reports.

If you believe this is an error, contact the moderation team.

When unbanned:

Restore reporting access.

==================================================
21. BROADCAST SYSTEM
==================================================

Admin Panel → 📢 Broadcast

Ask admin to send a message.

Then show preview:

📢 BROADCAST PREVIEW

{message}

Send this message to all bot users?

Buttons:

✅ Send Broadcast
❌ Cancel

After completion:

✅ BROADCAST COMPLETED

Successfully Delivered: {count}
Failed: {count}

Support text, photos, videos, and documents where possible by copying the original Telegram message.

==================================================
22. ADMIN LOGS
==================================================

Store important admin actions:

- Report approved
- Report rejected
- More proof requested
- Reporter banned
- Reporter unbanned
- Broadcast sent

Each log should store:

- Admin ID
- Admin username
- Action
- Report ID if applicable
- Target user if applicable
- Date and time

Admin panel should display recent logs with pagination.

==================================================
23. DATABASE
==================================================

Use persistent SQLite database storage.

Create tables for:

USERS:
- telegram_id
- username
- first_name
- joined_at
- is_banned

REPORTS:
- id
- report_id
- reporter_id
- reporter_username
- platform
- accused_username
- accused_user_id
- deal_value
- description
- evidence_link
- status
- rejection_reason
- more_proof_request
- admin_id
- admin_message_id
- channel_message_id
- created_at
- reviewed_at

ADMIN_LOGS:
- id
- admin_id
- admin_username
- action
- report_id
- target_user_id
- created_at

==================================================
24. SECURITY AND VALIDATION
==================================================

Implement:

- Admin-only callback validation
- Persistent database
- HTML escaping for all user-generated content
- Telegram link validation
- Username validation
- Numeric User ID validation
- Duplicate callback protection
- Prevent a report from being approved or rejected twice
- Rate limiting for report submissions
- Reporter ban system
- Safe exception handling
- Logging
- Database initialization on startup
- Environment variable validation
- Graceful handling when users block the bot
- Graceful handling when a channel post fails
- Do not mark a report approved if publishing to @avoidrep fails
- Store channel message IDs after successful publication
- Preserve all report data after bot restart

==================================================
25. ENVIRONMENT VARIABLES
==================================================

Use:

BOT_TOKEN=
ADMIN_IDS=
ADMIN_CHAT_ID=
CHANNEL_USERNAME=@avoidrep

ADMIN_IDS must support multiple numeric Telegram IDs separated by commas.

Example:

ADMIN_IDS=123456789,987654321

==================================================
26. PROJECT FILES
==================================================

Generate the complete working project with:

bot.py
database.py
requirements.txt
.env.example
.gitignore
README.md

Use Python with aiogram 3.x.

The project must be complete and directly runnable.

Do not give pseudocode.
Do not leave TODO sections.
Do not omit functions.
Do not use placeholder logic except for environment variable values.
Make every button functional.
Make every state transition functional.
Make all database operations functional.
Make all admin actions functional.
Make the project compatible with GitHub deployment and standard Python hosting.

The final result should be a complete, polished, working AVOID REPORTS Telegram bot for @avoidrep.
