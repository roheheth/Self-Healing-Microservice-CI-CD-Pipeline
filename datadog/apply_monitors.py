#!/usr/bin/env python3
"""
Datadog Monitor-as-Code Provisioning Script
Idempotently creates or updates monitors defined in monitors.json using the Datadog REST API.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional
import requests


class DatadogMonitorManager:
    def __init__(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        site: str = "datadoghq.com",
        dry_run: bool = False,
    ):
        self.api_key = api_key or os.getenv("DD_API_KEY")
        self.app_key = app_key or os.getenv("DD_APP_KEY")
        self.site = os.getenv("DD_SITE", site)
        self.base_url = f"https://api.{self.site}/api/v1"
        self.dry_run = dry_run

        self.headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": self.api_key or "",
            "DD-APPLICATION-KEY": self.app_key or "",
        }

    def validate_keys(self) -> bool:
        if self.dry_run:
            return True
        if not self.api_key or not self.app_key:
            print("[WARN] DD_API_KEY or DD_APP_KEY not set in environment.")
            print("[INFO] Set environment variables to deploy live to Datadog:")
            print("       $env:DD_API_KEY='<your_api_key>'")
            print("       $env:DD_APP_KEY='<your_app_key>'")
            return False
        return True

    def get_existing_monitors(self) -> Dict[str, Dict]:
        """Fetch all existing monitors tagged tier:2-enhancement or matching service."""
        if not self.validate_keys() or self.dry_run:
            return {}

        url = f"{self.base_url}/monitor"
        params = {"tags": "tier:2-enhancement"}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                monitors = resp.json()
                return {m["name"]: m for m in monitors}
            else:
                print(f"[ERROR] Failed to fetch monitors ({resp.status_code}): {resp.text}")
                return {}
        except Exception as e:
            print(f"[ERROR] Connection to Datadog API failed: {e}")
            return {}

    def apply_monitors(self, config_path: str):
        if not os.path.exists(config_path):
            print(f"[ERROR] Configuration file not found: {config_path}")
            sys.exit(1)

        with open(config_path, "r", encoding="utf-8") as f:
            monitors_def: List[Dict] = json.load(f)

        print(f"[INFO] Loaded {len(monitors_def)} monitor definitions from {config_path}")
        print(f"[INFO] Target Datadog Site: api.{self.site}")
        print(f"[INFO] Mode: {'DRY RUN (Validation Only)' if self.dry_run else 'LIVE UPSERT'}\n")

        existing_monitors = self.get_existing_monitors()

        for monitor in monitors_def:
            name = monitor["name"]
            print(f"-------------------------------------------------------------")
            print(f"Monitor: '{name}'")
            print(f"Type:    {monitor.get('type')}")
            print(f"Query:   {monitor.get('query')}")

            if self.dry_run or not self.validate_keys():
                print(f"Status:  [DRY-RUN VALIDATED] Ready for upsert.")
                continue

            if name in existing_monitors:
                monitor_id = existing_monitors[name]["id"]
                print(f"Action:  Updating existing monitor (ID: {monitor_id})...")
                url = f"{self.base_url}/monitor/{monitor_id}"
                resp = requests.put(url, headers=self.headers, json=monitor, timeout=10)
                if resp.status_code == 200:
                    print(f"Result:  ✅ Monitor updated successfully.")
                else:
                    print(f"Result:  ❌ Update failed ({resp.status_code}): {resp.text}")
            else:
                print(f"Action:  Creating new monitor...")
                url = f"{self.base_url}/monitor"
                resp = requests.post(url, headers=self.headers, json=monitor, timeout=10)
                if resp.status_code == 200:
                    created_id = resp.json().get("id")
                    print(f"Result:  ✅ Monitor created successfully (ID: {created_id}).")
                else:
                    print(f"Result:  ❌ Creation failed ({resp.status_code}): {resp.text}")

        print(f"-------------------------------------------------------------")
        print(f"\n[INFO] Monitor-as-Code execution completed.")


def main():
    parser = argparse.ArgumentParser(description="Datadog Monitor-as-Code Provisioning Tool")
    parser.add_argument("--config", default="datadog/monitors.json", help="Path to monitors.json definition")
    parser.add_argument("--webhook", default="datadog/webhook-config.json", help="Path to webhook-config.json definition")
    parser.add_argument("--site", default="datadoghq.com", help="Datadog site (datadoghq.com, datadoghq.eu, etc.)")
    parser.add_argument("--dry-run", action="store_true", help="Validate definitions without applying changes")

    args = parser.parse_args()

    manager = DatadogMonitorManager(
        site=args.site,
        dry_run=args.dry_run,
    )
    manager.apply_monitors(config_path=args.config)


if __name__ == "__main__":
    main()
