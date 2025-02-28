users_data = [
    {"email": "john.doe@example.com", "name": "John Doe", "profile_pic": None},
    {"email": "jane.doe@example.com", "name": "Jane Doe", "profile_pic": None}
]

roles_data = [
    {"name": "Admin"},
    {"name": "User"}
]

projects_data = [
    {"name": "Project A"},
    {"name": "Project B"}
]


# Create roles and projects
roles = [Role(**role) for role in roles_data]
projects = [Project(**project) for project in projects_data]

# Adding roles and projects to the session
session.add_all(roles)
session.add_all(projects)
session.commit()

# Create users and associate roles and projects
for user_data in users_data:
    user = User(**user_data)
    user.roles.append(roles[0])  # Example: Assign all users the "Admin" role
    user.projects.extend(projects)  # Assign all projects to each user
    session.add(user)

session.commit()

# Close the session
session.close()