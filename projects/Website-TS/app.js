const platformConfig = [
  {
    name: "Cohesity",
    summary: "Cohesity troubleshooting entry points for clusters, jobs, and incident context.",
    groups: [
      {
        title: "Agents",
        links: [
          { label: "Cohesity Agent Hub", href: "#" },
          { label: "Cluster Health Agent", href: "#" }
        ]
      },
      {
        title: "Isolated Web Searches",
        links: [
          { label: "KB + Error Code Search", href: "#" },
          { label: "Version-specific Search", href: "#" }
        ]
      },
      {
        title: "ServiceNow History",
        links: [
          { label: "Recent Cohesity Incidents", href: "#" },
          { label: "Recurring Ticket Patterns", href: "#" }
        ]
      }
    ]
  },
  {
    name: "Veeam",
    summary: "Veeam backup, repository, and proxy troubleshooting workflows.",
    groups: [
      {
        title: "Agents",
        links: [
          { label: "Veeam Agent Hub", href: "#" },
          { label: "Job Failure Analyzer", href: "#" }
        ]
      },
      {
        title: "Isolated Web Searches",
        links: [
          { label: "Veeam KB Search", href: "#" },
          { label: "Compatibility Search", href: "#" }
        ]
      },
      {
        title: "ServiceNow History",
        links: [
          { label: "Recent Veeam Tickets", href: "#" },
          { label: "Escalation History", href: "#" }
        ]
      }
    ]
  },
  {
    name: "Commvault",
    summary: "Commvault task-level diagnostics with quick jump tools.",
    groups: [
      {
        title: "Agents",
        links: [
          { label: "Commvault Agent Hub", href: "#" },
          { label: "Storage Policy Inspector", href: "#" }
        ]
      },
      {
        title: "Isolated Web Searches",
        links: [
          { label: "Known Issues Search", href: "#" },
          { label: "Patch Note Search", href: "#" }
        ]
      },
      {
        title: "ServiceNow History",
        links: [
          { label: "Open Commvault Cases", href: "#" },
          { label: "Top Repeat Issues", href: "#" }
        ]
      }
    ]
  },
  {
    name: "NetApp",
    summary: "NetApp troubleshooting checkpoints for storage and snapshot operations.",
    groups: [
      {
        title: "Agents",
        links: [
          { label: "NetApp Agent Hub", href: "#" },
          { label: "Snapshot Failure Agent", href: "#" }
        ]
      },
      {
        title: "Isolated Web Searches",
        links: [
          { label: "TR + KB Search", href: "#" },
          { label: "ONTAP Release Notes Search", href: "#" }
        ]
      },
      {
        title: "ServiceNow History",
        links: [
          { label: "NetApp Incident Timeline", href: "#" },
          { label: "Case Resolution Library", href: "#" }
        ]
      }
    ]
  },
  {
    name: "Quantum",
    summary: "Quantum backup and appliance diagnostics tools in one drill-down view.",
    groups: [
      {
        title: "Agents",
        links: [
          { label: "Quantum Agent Hub", href: "#" },
          { label: "Appliance Status Agent", href: "#" }
        ]
      },
      {
        title: "Isolated Web Searches",
        links: [
          { label: "Quantum Knowledge Search", href: "#" },
          { label: "Firmware Search", href: "#" }
        ]
      },
      {
        title: "ServiceNow History",
        links: [
          { label: "Quantum Support Cases", href: "#" },
          { label: "Trend by Customer", href: "#" }
        ]
      }
    ]
  }
];

const buttonContainer = document.getElementById("platform-buttons");
const toolGroupsContainer = document.getElementById("tool-groups");
const activeLabel = document.getElementById("active-platform-label");
const activeSummary = document.getElementById("active-platform-summary");

function renderToolGroups(platform) {
  toolGroupsContainer.innerHTML = "";

  platform.groups.forEach((group) => {
    const groupEl = document.createElement("section");
    groupEl.className = "tool-group";

    const heading = document.createElement("h4");
    heading.textContent = group.title;

    const list = document.createElement("ul");

    group.links.forEach((item) => {
      const listItem = document.createElement("li");
      const link = document.createElement("a");
      link.textContent = item.label;
      link.href = item.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";

      listItem.appendChild(link);
      list.appendChild(listItem);
    });

    groupEl.appendChild(heading);
    groupEl.appendChild(list);
    toolGroupsContainer.appendChild(groupEl);
  });
}

function setActivePlatform(name) {
  const platform = platformConfig.find((entry) => entry.name === name);
  if (!platform) {
    return;
  }

  activeLabel.textContent = platform.name;
  activeSummary.textContent = platform.summary;
  renderToolGroups(platform);

  const buttons = buttonContainer.querySelectorAll(".platform-btn");
  buttons.forEach((button) => {
    const isActive = button.dataset.platform === name;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}

function buildButtons() {
  platformConfig.forEach((platform, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "platform-btn";
    button.dataset.platform = platform.name;
    button.setAttribute("aria-pressed", "false");
    button.textContent = platform.name;
    button.style.animationDelay = `${80 * index}ms`;

    button.addEventListener("click", () => setActivePlatform(platform.name));
    buttonContainer.appendChild(button);
  });
}

buildButtons();
setActivePlatform(platformConfig[0].name);
