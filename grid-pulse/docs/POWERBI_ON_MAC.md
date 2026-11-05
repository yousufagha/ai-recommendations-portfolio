# Power BI on a Mac, without a VM

Not the current route: Grid Pulse now uses Looker Studio. Kept in case Power BI is needed later.

Facts checked against Microsoft documentation on 5 November 2026. Items marked "untested" have not been tried on this project.

## How it works

1. **Build on the Mac:** the model and report are text files in Git.
2. **Deploy from the Mac:** [`fabric-cicd`](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-deploy-fabric-cicd), Microsoft's Python library (free), sends them to a cloud workspace. Python 3.12 is already in use here.
3. **Test from the Mac:** the [Execute Queries API](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries) runs DAX in the cloud, so the golden values can be compared automatically. It needs a tenant setting turned on.
4. **Polish in the browser:** [web modelling](https://learn.microsoft.com/en-us/power-bi/transform-model/service-edit-data-models) covers Power Query, measures, relationships, row-level security and refresh. Reports are edited in the browser too.
5. **Bring it back to Git:** [Fabric REST APIs export reports as PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), so browser edits can return to the repo (untested).

## What you need to do

The account steps are yours, because they involve creating an account and entering card details.

1. Start a [Microsoft 365 trial](https://learn.microsoft.com/en-us/power-bi/fundamentals/service-self-service-signup-purchase-for-power-bi). Gmail cannot sign up for Power BI directly. This creates an `onmicrosoft.com` work account and a tenant where you are admin. **Cost:** free for up to 30 days, credit card required. Cancel before 30 days if you do not want to pay.
2. Sign in at [app.fabric.microsoft.com](https://app.fabric.microsoft.com) and start the [Fabric trial](https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial) from the account menu. **Cost:** free for 60 days. Availability is not guaranteed.
3. Create a workspace named `Grid Pulse Dev` and set its type to Fabric Trial.
4. In the admin portal, turn on **Dataset Execute Queries REST API** and **Publish to web**.

**Timing:** do this only when the model is ready to deploy, because the trial clocks start at sign-up.

## What you give up, compared with Desktop

Microsoft lists these gaps in web modelling:

- The "View as" dialog, which matters for Dubai. Execute Queries can test a role by impersonating a user, but not with a service principal (untested).
- Q&A setup, including synonyms.
- Sensitivity labelling of the report, and feature tables.
- Direct Lake tables cannot use the Power Query editor. Grid Pulse uses import mode.

Not confirmed either way until tried: authoring calculation groups and field parameters in the browser (the deploy route should carry them as TMDL regardless), mobile layout and Performance Analyzer. Vendor pages describe browser authoring as limited, but some of them sell VM software.

## When it ends

- A portfolio on GitHub keeps its files, screenshots and video after the trial.
- A public link needs a licensed owner, so keeping it live after the trial is paid.
- Trial data is not a permanent home: non-Power BI Fabric items become inactive once the Fabric trial ends.

## Fallback

If something essential is blocked, use a Windows 11 ARM VM, after a date-visual smoke test.
