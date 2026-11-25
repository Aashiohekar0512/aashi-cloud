const API = "http://127.0.0.1:8001";

// LOAD PROJECTS
async function loadProjects() {
    const list = document.getElementById("projectList");

    try {
        const response = await fetch(API + "/projects");

        if (!response.ok) throw new Error("API Error");

        const projects = await response.json();

        document.getElementById("totalProjects").textContent =
            projects.length;

        list.innerHTML = "";

        if (projects.length === 0) {
            list.textContent = "No projects yet.";
            return;
        }

        projects.forEach(project => {
            const item = document.createElement("div");

            item.style.padding = "15px";
            item.style.borderBottom = "1px solid #334155";

            const name = document.createElement("h3");
            name.textContent = project.name;

            const details = document.createElement("p");
            details.textContent =
                project.framework + " | " + project.status;

            const edit = document.createElement("button");
            edit.textContent = "Edit";
            edit.onclick = () => editProject(project);

            const remove = document.createElement("button");
            remove.textContent = "Delete";
            remove.style.marginLeft = "10px";
            remove.onclick = () => deleteProject(project.id);

            item.appendChild(name);
            item.appendChild(details);
            item.appendChild(edit);
            item.appendChild(remove);

            list.appendChild(item);
        });

    } catch (error) {
        list.textContent = "Cannot connect to backend.";
        console.error(error);
    }
}

// OPEN FORM
function openProjectForm() {
    document.getElementById("projectForm").hidden = false;
}

function closeProjectForm() {
    document.getElementById("projectForm").hidden = true;
}

// CREATE PROJECT
async function createProject() {
    const name = document.getElementById("projectName").value.trim();
    const framework =
        document.getElementById("projectFramework").value.trim();

    if (!name || !framework) {
        alert("Please enter project name and framework");
        return;
    }

    try {
        const response = await fetch(API + "/projects", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                framework
            })
        });

        if (!response.ok) throw new Error("Creation failed");

        alert("Project created successfully!");

        document.getElementById("projectName").value = "";
        document.getElementById("projectFramework").value = "";

        closeProjectForm();
        loadProjects();

    } catch (error) {
        alert("Project creation failed!");
        console.error(error);
    }
}

// EDIT PROJECT
async function editProject(project) {
    const name = prompt("Enter new project name:", project.name);
    if (name === null || !name.trim()) return;

    const framework = prompt(
        "Enter framework:",
        project.framework
    );

    if (framework === null || !framework.trim()) return;

    const status = prompt(
        "Enter status:",
        project.status
    );

    if (status === null || !status.trim()) return;

    try {
        const response = await fetch(
            API + "/projects/" + project.id,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    name: name.trim(),
                    framework: framework.trim(),
                    status: status.trim()
                })
            }
        );

        if (!response.ok) throw new Error("Update failed");

        alert("Project updated successfully!");
        loadProjects();

    } catch (error) {
        alert("Project update failed!");
        console.error(error);
    }
}

// DELETE PROJECT
async function deleteProject(id) {
    if (!confirm("Are you sure you want to delete this project?")) {
        return;
    }

    try {
        const response = await fetch(
            API + "/projects/" + id,
            {
                method: "DELETE"
            }
        );

        if (!response.ok) throw new Error("Delete failed");

        alert("Project deleted successfully!");
        loadProjects();

    } catch (error) {
        alert("Project deletion failed!");
        console.error(error);
    }
}

// INITIAL LOAD
loadProjects();