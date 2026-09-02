using System;

internal static class AccountWatcherPolicyTests
{
    private static int failures;

    private static void Assert(bool condition, string name)
    {
        if (!condition)
        {
            Console.Error.WriteLine("FAIL " + name);
            failures++;
        }
        else
        {
            Console.WriteLine("PASS " + name);
        }
    }

    public static int Main()
    {
        DateTime now = new DateTime(2026, 8, 30, 12, 0, 0, DateTimeKind.Utc);

        Assert(!AntigravityAccountWatcher.AccountIdChanged("A", "A"),
            "same account file write does not schedule repair");
        Assert(AntigravityAccountWatcher.AccountIdChanged("B", "A"),
            "A to B schedules account repair");

        string handled = "A";
        int launches = 0;
        if (AntigravityAccountWatcher.AccountIdChanged("B", handled))
        {
            launches++;
            handled = "B";
        }
        if (AntigravityAccountWatcher.AccountIdChanged("B", handled)) launches++;
        Assert(launches == 1, "repeated B write does not launch twice");

        Assert(!AntigravityAccountWatcher.CanStartRepair(true, false, true, now, now, now),
            "repair in progress blocks concurrent launch");
        Assert(!AntigravityAccountWatcher.CanStartRepair(true, true, false, now, now, now),
            "running launcher blocks concurrent launch");
        Assert(!AntigravityAccountWatcher.CanStartRepair(true, false, false, now, now, now.AddSeconds(30)),
            "success cooldown blocks event storm");
        Assert(AntigravityAccountWatcher.CanStartRepair(true, false, false, now, now, now),
            "runtime proxy bypass remains eligible");

        int attempts = 0;
        while (attempts < AntigravityAccountWatcher.MaxRepairAttempts) attempts++;
        Assert(attempts == 3, "failed repair retry count is bounded");
        Assert(AntigravityAccountWatcher.RetryDelaySeconds(1) == 10 &&
            AntigravityAccountWatcher.RetryDelaySeconds(2) == 20 &&
            AntigravityAccountWatcher.RetryDelaySeconds(3) == 40,
            "failed repair retries use backoff");
        Assert(AntigravityAccountWatcher.ExhaustedHealthRetrySeconds >= 300,
            "exhausted health recovery schedules a slow retry cycle");

        Assert(!AntigravityAccountWatcher.HealthRepairDue(2, false),
            "two transient health failures do not switch nodes");
        Assert(AntigravityAccountWatcher.HealthRepairDue(3, false),
            "three consecutive health failures trigger recovery");
        Assert(AntigravityAccountWatcher.HealthRepairDue(0, true),
            "new location failure triggers candidate rotation");
        Assert(AntigravityAccountWatcher.RecoveryModeForReason("proxy_network_failure") == "NetworkFailure" &&
            AntigravityAccountWatcher.RecoveryModeForReason("proxy_location_failure") == "LocationFailure" &&
            AntigravityAccountWatcher.RecoveryModeForReason("cockpit_account_changed") == "Startup",
            "repair reasons map to bounded supervisor recovery modes");

        return failures == 0 ? 0 : 1;
    }
}
