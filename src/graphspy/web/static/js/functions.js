// ========== Access Tokens ==========

function setActiveAccessToken(access_token_id, silent = false) {
    var active_access_token = access_token_id;
    setCookie("access_token_id", active_access_token);
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/active_access_token/" + active_access_token
    });
    if (document.getElementById("access_token_id")) {
        document.getElementById("access_token_id").value = active_access_token;
    }
    obtainAccessTokenInfo();
    if (!silent) {
        bootstrapToast("Activate Access Token", `[Succes] Activated access token with ID '${active_access_token}'`, "info");
    }
};

function getActiveAccessToken(access_token_field = null) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/active_access_token"
    });
    active_access_token = response.responseText
    setCookie("access_token_id", active_access_token);
    if (access_token_field) {
        access_token_field.value = active_access_token;
    }
};

function deleteAccessToken(token_id) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/delete_access_token/" + token_id
    });
    bootstrapToast("Delete access token", `[Success] Deleted access token with ID ${token_id}.`);
};

// ========== Refresh Tokens ==========

function setActiveRefreshToken(refresh_token_id) {
    var active_refresh_token = refresh_token_id;
    setCookie("refresh_token_id", active_refresh_token);
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/active_refresh_token/" + active_refresh_token
    });
    if (document.getElementById("refresh_token_id")) {
        document.getElementById("refresh_token_id").value = active_refresh_token;
    }
    obtainRefreshTokenInfo();
    bootstrapToast("Activate Refresh Token", `[Succes] Activated refresh token with ID '${active_refresh_token}'`, "info");
};

function getActiveRefreshToken(refresh_token_field) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/active_refresh_token"
    });
    active_refresh_token = response.responseText
    setCookie("refresh_token_id", active_refresh_token);
    if (refresh_token_field) {
        refresh_token_field.value = active_refresh_token
    }
};

function refreshToAccessToken(refresh_token_id, client_id, resource = "", scope = "", store_refresh_token = false, activate = false, api_version = 1) {
    var post_data = {
        "refresh_token_id": refresh_token_id,
        "client_id": client_id,
        "resource": resource,
        "scope": scope,
        "api_version": api_version
    };
    if (store_refresh_token) {
        post_data["store_refresh_token"] = 1;
    }
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/refresh_to_access_token",
        data: post_data,
        success: function (response) {
            access_token_id = response;
            if (activate) {
                setActiveAccessToken(access_token_id, true);
                bootstrapToast("Refresh To Access Token", `[Succes] Obtained and activated access token with ID '${access_token_id}'`, "success");
            } else {
                bootstrapToast("Refresh To Access Token", `[Succes] Obtained access token with ID '${access_token_id}'`, "success");
            }
        },
        error: function (xhr, status, error) {
            bootstrapToast("Refresh To Access Token", xhr.responseText, "danger");
        }
    });
};

function deleteRefreshToken(token_id) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/delete_refresh_token/" + token_id
    });
    bootstrapToast("Delete refresh token", `[Success] Deleted refresh token with ID ${token_id}.`);
}

// ========== PRT ==========

function refreshPrtToAccessToken(prt_id, client_id, resource = "", scope = "", refresh_prt = true, redirect_uri = null, activate = false, api_version = 1) {
    var post_data = {
        "prt_id": prt_id,
        "client_id": client_id,
        "resource": resource,
        "scope": scope,
        "api_version": api_version,
        "refresh_prt": refresh_prt
    };
    if (redirect_uri) {
        post_data["redirect_uri"] = redirect_uri;
    }
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/refresh_prt_to_access_token",
        data: post_data,
        success: function (response) {
            access_token_id = response.data.access_token_id;
            if (activate) {
                setActiveAccessToken(access_token_id, true);
                bootstrapToast("PRT To Access Token", `[Success] Obtained and activated access token with ID '${access_token_id}'`, "success");
            } else {
                bootstrapToast("PRT To Access Token", `[Success] Obtained access token with ID '${access_token_id}'`, "success");
            }
        },
        error: function (xhr, status, error) {
            bootstrapToast("PRT To Access Token", xhr.responseJSON.message, "danger");
        }
    });
};


function getActivePrt(element) {
    $.get("/api/active_prt", function(data) {
        element.value = data;
    });
}

function setActivePrt(id) {
    $.get("/api/active_prt/" + id, function(data) {
        if (document.getElementById("active_prt_id")) {
            document.getElementById("active_prt_id").value = id;
        }
        bootstrapToast("Active PRT", `[Success] Activated PRT with ID ${id}`, "info");
        reloadTables();
    });
}

function loadDeviceModalTable() {
    // Create device selection modal
    let deviceModal = createModal("device_modal", "Select Device", `
        <div id="dTable" class="box-body table-responsive" style="padding:10px;">
            <table id="device_modal_table" class="table table-striped nowrap" style="width:100%">
            </table>
        </div>
    `, "modal-xl");
    // Initialize device selection table
    let deviceTable = new DataTable('#device_modal_table', {
        ajax: {
            url: '/api/list_device_certificates', dataSrc: "data"
        },
        columns: [
            {
                className: 'select-control table-control',
                orderable: false,
                data: null,
                defaultContent: '<i class="fi fi-rr-check" title="Select Device" style="cursor: pointer"></i>',
                'width': '40px'
            },
            { data: 'id', title: 'ID', 'width': '60px' },
            { data: 'device_id', title: 'Device ID', 'width': '320px' },
            { data: 'device_name', title: 'Device Name', 'width': '250px' },
            { data: 'join_type', title: 'Join Type', 'width': '150px' },
            { data: 'device_type', title: 'Device Type', 'width': '150px' }
        ],
        order: [[1, 'desc']]
    });
    deviceTable.on('click', 'td.select-control', function (e) {
        let tr = e.target.closest('tr');
        let row = deviceTable.row(tr);
        $('input#device_id').val(row.data().device_id);
        $('input#import_device_id').val(row.data().device_id);
        $('#device_modal').modal('hide');
    });
}

function loadWinHelloModalTable() {
    // Create WinHello key selection modal
    let winhelloModal = createModal("winhello_modal", "Select WinHello Key", `
        <div id="dTable" class="box-body table-responsive" style="padding:10px;">
            <table id="winhello_modal_table" class="table table-striped nowrap" style="width:100%">
            </table>
        </div>
    `, "modal-xl");
    // Initialize WinHello key selection table
    let winhelloTable = new DataTable('#winhello_modal_table', {
        ajax: {
            url: '/api/list_winhello_keys', dataSrc: "data"
        },
        columns: [
            {
                className: 'select-control table-control',
                orderable: false,
                data: null,
                defaultContent: '<i class="fi fi-rr-check" title="Select WinHello Key" style="cursor: pointer"></i>',
                'width': '40px'
            },
            { data: 'id', title: 'ID', 'width': '60px' },
            { 
                data: 'stored_at', 
                title: 'Stored At', 
                'width': '170px',
                render: function(data) {
                    return new Date(data * 1000).toLocaleString();
                }
            },
            { data: 'user', title: 'User', 'width': '370px' },
            { data: 'device_id', title: 'Device ID', 'width': '370px' }
        ],
        order: [[1, 'desc']]
    });
    winhelloTable.on('click', 'td.select-control', function (e) {
        let tr = e.target.closest('tr');
        let row = winhelloTable.row(tr);
        $('input#winhello_id').val(row.data().id);
        $('#winhello_modal').modal('hide');
    });
}


// ========== Device Codes ==========

function generateDeviceCode(version, client_id, resource, scope, ngcmfa, cae, auto_action, auto_device_name, auto_join_type, auto_device_type, auto_os_version, auto_target_domain) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/generate_device_code",
        data: { 
            "version": version,
            "client_id": client_id,
            "resource": resource,
            "scope": scope,
            "ngcmfa": ngcmfa,
            "cae": cae,
            "auto_action": auto_action,
            "auto_device_name": auto_device_name,
            "auto_join_type": auto_join_type,
            "auto_device_type": auto_device_type,
            "auto_os_version": auto_os_version,
            "auto_target_domain": auto_target_domain
        }, 
        success: function(response){
            bootstrapToast("Device Code", `[Success] Generated Device Code with User Code '${response}'.`, "primary");
            reloadTables();
        },
        error: function (xhr, status, error) {
            bootstrapToast("Device Code", xhr.responseJSON.message, "danger");
        }
    });
}

function restartDeviceCodePolling() {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/restart_device_code_polling"
    });
    $('#device_codes').DataTable().ajax.reload(null, false);
    bootstrapToast("Restart polling", response.responseText);
}

// ========== MFA ==========

function validateCaptcha(access_token_id, challenge_id, captcha_solution, azure_region, challenge_type) {
    $.ajax({
        type: "POST",
        async: false,
        url: "/api/validate_captcha",
        data: {
            "access_token_id": access_token_id,
            "challenge_id": challenge_id,
            "captcha_solution": captcha_solution,
            "azure_region": azure_region,
            "challenge_type": challenge_type
        },
        success: function (response) {
            bootstrapToast("Validate Captcha", "Captcha solved! Try submitting the previous form again!", "success");
        },
        error: function (xhr, status, error) {
            bootstrapToast("Validate Captcha", xhr.responseText, "danger");
        }
    });
}

function verifySecurityInfo(access_token_id, security_info_type, verification_context, verification_data) {
    $.ajax({
        type: "POST",
        async: false,
        url: "/api/verify_security_info",
        data: {
            "access_token_id": access_token_id,
            "security_info_type": security_info_type,
            "verification_context": verification_context,
            "verification_data": verification_data
        },
        success: function (response) {
            if (response.hasOwnProperty("ErrorCode") && response.ErrorCode) {
                bootstrapToast("Verify Security Info", `An error occurred when trying to validate the provided info. Received Error Code ${response.ErrorCode}`, "danger");
                return;
            }
            bootstrapToast("Verify Security Info", "Info validated. Check if the MFA method was added correctly.", "success");
            $("#add_mfa_form #verification_container").hide();
            $("#add_mfa_form #user_input").val("");
        },
        error: function (xhr, status, error) {
            bootstrapToast("Verify Security Info", xhr.responseText, "danger");
        }
    });
}

function deleteSecurityInfo(access_token_id, security_info_type, data) {
    $.ajax({
        type: "POST",
        async: false,
        url: "/api/delete_security_info", dataType: "json",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
            "access_token_id": access_token_id,
            "security_info_type": security_info_type,
            "data": data
        }),
        success: function (response) {
            let successMessage = response.hasOwnProperty("DefaultMethodUpdated") && response.DefaultMethodUpdated ? `MFA Method deleted and default method updated to method type ${response.UpdatedDefaultMethod}` : "MFA Method deleted."
            bootstrapToast("Delete MFA Method", successMessage, "success");
        },
        error: function (xhr, status, error) {
            bootstrapToast("Delete MFA Method", xhr.responseText, "danger");
        }
    });
}

function generateOtpCode(secret_key) {
    response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/generate_otp_code",
        data: {
            "secret_key": secret_key,
        }
    });
    if (response.status != 200) {
        bootstrapToast("Generate OTP Code", response.responseText, "danger");
        return false;
    }
    return response.responseText
}

function deleteGraphspyOtp(otp_code_id) {
    response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/delete_graphspy_otp",
        data: {
            "otp_code_id": otp_code_id,
        },
        success: function (response) {
            bootstrapToast("Delete OTP Code", response, "success");
        },
        error: function (xhr, status, error) {
            bootstrapToast("Delete OTP Code", xhr.responseText, "danger");
        }
    });
}

// ========== Graph ==========


function graphDownload(drive_id, item_id, access_token_id) {
    let graph_uri = "https://graph.microsoft.com/v1.0/drives/" + drive_id + "/items/" + item_id
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/generic_graph",
        dataSrc: "",
        data: { "graph_uri": graph_uri, "access_token_id": access_token_id },
    });
    let response_json = JSON.parse(response.responseText)
    window.location = response_json["@microsoft.graph.downloadUrl"];
}

function graphUpload(drive_id, path, file, access_token_id, callback) {
    base_url = drive_id == "onedrive" ? "https://graph.microsoft.com/v1.0/me/drive" : `https://graph.microsoft.com/v1.0/drives/${drive_id}`;
    let formData = new FormData();
    formData.append("file", file);
    formData.append("upload_uri", `${base_url}/root:/${path}/${file.name}:/content`);
    formData.append("access_token_id", access_token_id);

    $.ajax({
        url: "/api/generic_graph_upload",
        type: "POST",
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            bootstrapToast("Upload File", "File uploaded successfully.", "success");
            if (callback) callback();
        },
        error: function(xhr, status, error) {
            bootstrapToast("Upload File", "Failed to upload file. Status code: " + xhr.status + ", Response: " + xhr.responseText, "danger");
            if (callback) callback();
        }
    });
}
function graphDelete(drive_id, item_id, access_token_id, callback) {
    let graph_uri = `https://graph.microsoft.com/v1.0/drives/${drive_id}/items/${item_id}`
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/custom_api_request",
        dataSrc: "",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
            "uri": graph_uri,
            "access_token_id": access_token_id,
            "method": "DELETE"
        }),
        success: function (response) {
            if ([200, 204].includes(response.response_status_code)) {
                bootstrapToast("Delete Item", "Item deleted successfully.", "success");
            } else {
                bootstrapToast("Delete Item", "Failed to delete item. Status code: " + response.response_status_code + ", Response: " + response.response_text, "danger");
            }
            if (callback) callback();
        },
        error: function (xhr, status, error) {
            bootstrapToast("Delete Item", "Failed to delete item. Status code: " + xhr.status + ", Response: " + xhr.responseText, "danger");
            if (callback) callback();
        }
    });
}

// ========== Database ==========

function deleteDatabase(database_name) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/delete_database",
        data: { "database": database_name }
    });
    bootstrapToast("Delete database", response.responseText)
}

function activateDatabase(database_name) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/activate_database",
        data: { "database": database_name }
    });
    obtainAccessTokenInfo();
    obtainRefreshTokenInfo();
    obtainPersistentSettings();
    bootstrapToast("Acticate database", response.responseText)
}

function createDatabase(database_name) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/create_database",
        data: { "database": database_name }
    });
    obtainAccessTokenInfo();
    obtainRefreshTokenInfo();
    obtainPersistentSettings();
    bootstrapToast("Create database", response.responseText)
}

function duplicateDatabase(database_name) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/duplicate_database",
        data: { "database": database_name }
    });
    bootstrapToast("Duplicate database", response.responseText)
}

// ========== Teams ==========

async function getTeamsConversations(access_token_id) {
    let response = await $.ajax({
        type: "POST",
        async: true,
        url: "/api/get_teams_conversations",
        data: { "access_token_id": access_token_id },
        error: function (jqXHR, textStatus, errorThrown) {
            if (jqXHR.status >= 400) {
                bootstrapToast("Teams Conversations", jqXHR.responseText, "danger");
                return;
            }
        }
    });
    return response;
}

function getTeamsConversationMessages(access_token_id, conversation_link) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/get_teams_conversation_messages",
        data: { "access_token_id": access_token_id, "conversation_link": conversation_link }
    });
    if (response.status >= 400) {
        bootstrapToast("Teams Conversation Messages", response.responseText, "danger");
        return;
    }
    return response.responseJSON;
}

function sendTeamsConversationMessage(access_token_id, conversation_link, message_content) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/send_teams_conversation_message",
        data: {
            "access_token_id": access_token_id,
            "conversation_link": conversation_link,
            "message_content": message_content
        }
    });
    if (response.status >= 400) {
        bootstrapToast("Send Teams Messages", response.responseText, "danger");
        return;
    }
    bootstrapToast("Send Teams Messages", `Teams message with ID ${response.responseText} created.`, "success");
    return response.responseText;
}

function getTeamsConversationMembers(access_token_id, conversation_id) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/get_teams_conversation_members",
        data: { "access_token_id": access_token_id, "conversation_id": conversation_id }
    });
    if (response.status >= 400) {
        bootstrapToast("Teams Members", response.responseText, "danger");
        return;
    }
    return response.responseJSON;
}

function getTeamsUserDetails(access_token_id, user_id, external=false) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: `/api/get_teams_user_details?access_token_id=${access_token_id}&user_id=${user_id}&external=${external.toString()}`
    });
    if (response.status >= 400) {
        bootstrapToast("Get Teams User Details", response.responseText, "danger");
        return;
    }
    return response.responseJSON;
}

function createTeamsConversation(access_token_id, members, type = "group_chat", topic = null, message_content = null) {
    body = {
        "access_token_id": access_token_id,
        "members": members,
        "type": type
    };
    if (topic){
        body["topic"] = topic
    };
    if (message_content){
        body["message_content"] = message_content
    };
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/create_teams_conversation",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify(body)
    });
    if (response.status >= 400) {
        bootstrapToast("Create Teams Conversation", response.responseText, "danger");
        return;
    }
    bootstrapToast("Create Teams Conversation", `Successfully created ${response.responseJSON.length} conversation(s).`, "success");
    return response.responseJSON;
}

// ========== Entra ID ==========

function getEntraUserDetails(access_token_id, user_id) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: `/api/get_entra_user_details/${encodeURIComponent(user_id)}?access_token_id=${access_token_id}`
    });
    if (response.status >= 400) {
        bootstrapToast("Get Entra ID User Details", response.responseText, "danger");
        return;
    }
    return response.responseJSON;
}

function openUserDetailsModal(access_token_id, user_id) {
    // Show loading cursor
    $('html, body').css('cursor', 'wait');
    let entraUserDetails = getEntraUserDetails(access_token_id, user_id);
    // Remove loading cursor
    $('html, body').css('cursor', '');
    let modalBody = `
        <div class="row ms-0" id="user_details_header_overview">
            <h5>Overview</h5>
            <ul id="user_details_overview" class="list-group">
            </ul>
        </div>
        <div class="accordion" id="userDetailsAccordion">
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne" aria-controls="collapseOne">
                <b>Full details</b>
              </button>
            </h2>
            <div id="collapseOne" class="accordion-collapse collapse" data-bs-parent="#userDetailsAccordion">
              <div class="accordion-body" id="user_details_full">
              </div>
            </div>
          </div>
        </div>
        <hr>
        <div class="row" id="user_details_header_groups">
            <h5>Group Membership</h5>
            <table id="user_details_group_membership_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>Description</th>
                        <th>Security Enabled</th>
                        <th>Dynamic</th>
                        <th>Synced</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="user_details_header_roles">
            <h5>Directory Role Membership</h5>
            <table id="user_details_role_membership_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>Description</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="user_details_header_devices">
            <h5>Owned Devices</h5>
            <table id="user_details_owned_devices_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>OS</th>
                        <th>Type</th>
                        <th>Last Signin</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="user_details_header_app_roles">
            <h5>App Role Assignments</h5>
            <table id="user_details_app_role_assignment_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Resource ID</th>
                        <th>Resource Name</th>
                        <th>Created</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="user_details_header_api_perms">
            <h5>API Permissions</h5>
            <table id="user_details_api_permissions_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Client ID</th>
                        <th>Resource ID</th>
                        <th>Scope</th>
                    </tr>
                </thead>
            </table>
        </div>
        `;
    let modalNav = `
        <nav id="entra_user_details_modal_navbar" class="navbar">
          <ul class="nav nav-pills">
            <li class="nav-item">
              <a class="nav-link" href="#user_details_header_overview">Overview</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#user_details_header_groups">Groups</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#user_details_header_roles">Roles</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#user_details_header_devices">Devices</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#user_details_header_app_roles">App Roles</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#user_details_header_api_perms">API Perms</a>
            </li>
          </ul>
        </nav>
        `;
    let userGroupsModal = createModal("entra_user_details_modal", `User details '${entraUserDetails.displayName}'`, modalBody, "modal-xl");
    userGroupsModal.find(".modal-title").addClass("d-inline-block text-truncate").css("max-width", "350px");
    userGroupsModal.find(".modal-title").after(modalNav);
    userGroupsModal.find(".modal-body").attr("data-bs-spy", "scroll").attr("data-bs-target", "#entra_user_details_modal_navbar").attr("tabindex", "0");;
    userGroupsModal.on('shown.bs.modal', function () {
        bootstrap.ScrollSpy.getOrCreateInstance(this.querySelector('.modal-body')).refresh();
    });
    userGroupsModal.modal('show');
    function createDetailItem(key, value) {
        let item = $('<li class="list-group-item"></li>');
        item.append($('<b class="text-body-secondary"></b>').text(`${key}: `));
        item.append($('<span class="text-light-emphasis"></span>').text(value));
        return item;
    }
    let userDetailsOverview = userGroupsModal.find('#user_details_overview');
    userDetailsOverview.append(createDetailItem("ID", entraUserDetails.id));
    userDetailsOverview.append(createDetailItem("Security ID", entraUserDetails.securityIdentifier));
    userDetailsOverview.append(createDetailItem("Name", entraUserDetails.displayName));
    userDetailsOverview.append(createDetailItem("User Principal Name", entraUserDetails.userPrincipalName));
    userDetailsOverview.append(createDetailItem("Enabled", entraUserDetails.accountEnabled));
    userDetailsOverview.append(createDetailItem("Type", entraUserDetails.userType));
    if (entraUserDetails.mail) { userDetailsOverview.append(createDetailItem("Mail", entraUserDetails.mail))};
    if (entraUserDetails.mobilePhone) { userDetailsOverview.append(createDetailItem("Mobile", entraUserDetails.mobilePhone))};
    if (entraUserDetails.businessPhones.length) { userDetailsOverview.append(createDetailItem("Business Phones", entraUserDetails.businessPhones))};
    if (entraUserDetails.companyName) { userDetailsOverview.append(createDetailItem("Company", entraUserDetails.companyName))};
    if (entraUserDetails.department) { userDetailsOverview.append(createDetailItem("Department", entraUserDetails.department))};
    if (entraUserDetails.jobTitle) { userDetailsOverview.append(createDetailItem("Job Title", entraUserDetails.jobTitle))};
    if (entraUserDetails.country) { userDetailsOverview.append(createDetailItem("Country", entraUserDetails.country))};
    if (entraUserDetails.city) { userDetailsOverview.append(createDetailItem("City", entraUserDetails.city))};
    if (entraUserDetails.streetAddress) { userDetailsOverview.append(createDetailItem("Street Address", entraUserDetails.streetAddress))};
    userDetailsOverview.append(createDetailItem("Password Changed", entraUserDetails.lastPasswordChangeDateTime));
    userDetailsOverview.append(createDetailItem("Created", entraUserDetails.createdDateTime));
    userDetailsOverview.append(createDetailItem("Refresh Tokens Valid From", entraUserDetails.refreshTokensValidFromDateTime));
    if (entraUserDetails.onPremisesSyncEnabled) {
        userDetailsOverview.append(createDetailItem("On-Prem Synced", entraUserDetails.onPremisesSyncEnabled));
        userDetailsOverview.append(createDetailItem("On-Prem UPN", entraUserDetails.onPremisesUserPrincipalName));
        userDetailsOverview.append(createDetailItem("On-Prem SamAccountName", entraUserDetails.onPremisesSamAccountName));
        userDetailsOverview.append(createDetailItem("On-Prem DN", entraUserDetails.onPremisesDistinguishedName));
        userDetailsOverview.append(createDetailItem("On-Prem Last Sync", entraUserDetails.onPremisesLastSyncDateTime));
        userDetailsOverview.append(createDetailItem("On-Prem SID", entraUserDetails.onPremisesSecurityIdentifier));
        userDetailsOverview.append(createDetailItem("On-Prem Immutable ID", entraUserDetails.onPremisesImmutableId));
    } else {
        userDetailsOverview.append(createDetailItem("Synced", "false"));
    }
    userGroupsModal.find('#user_details_full').append(formatJsonCode(entraUserDetails));
    Prism.highlightAll();

    if ($.fn.dataTable.isDataTable(userGroupsModal.find('#user_details_group_membership_table')[0])) {
        userGroupsModal.find('#user_details_group_membership_table').DataTable().destroy();
        userGroupsModal.find('#user_details_group_membership_table').empty();
    }
    let userDetailsGroupMembershipTable = new DataTable(userGroupsModal.find('#user_details_group_membership_table')[0], {
        data: entraUserDetails.transitiveMemberOf.filter(object => object["@odata.type"] == "#microsoft.graph.group"),
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'group-details-control',
                orderable: false,
                data: null,
                defaultContent: '<i class="fi fi-rr-member-search" style="cursor: pointer" title="View Group Details"></i>',
                'width': '20px'
            },
            { data: 'displayName', title: "Display Name" },
            { data: 'description', title: "Description" },
            { data: 'securityEnabled', title: "Security Enabled", width: "10px" },
            {
                data: null,
                render: function (d, t, r) { return r.membershipRule ? "true" : "false"; },
                title: "Dynamic",
                width: '10px'
            },
            {
                data: null,
                render: function (d, t, r) { return r.onPremisesSyncEnabled ? "true" : "false"; },
                title: "Synced",
                width: '10px'
            }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    userDetailsGroupMembershipTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = userDetailsGroupMembershipTable.row(tr);
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
        }
        else {
            // Open this row
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
    userDetailsGroupMembershipTable.on('click', 'td.group-details-control', function (e) {
        let tr = e.target.closest('tr');
        let row = userDetailsGroupMembershipTable.row(tr);
        let groupData = row.data();
        if (groupData && groupData.id) {
            openGroupDetailsModal(access_token_id, groupData.id);
        }
    });
    if ($.fn.dataTable.isDataTable(userGroupsModal.find('#user_details_role_membership_table')[0])) {
        userGroupsModal.find('#user_details_role_membership_table').DataTable().destroy();
        userGroupsModal.find('#user_details_role_membership_table').empty();
    }
    let userDetailsRoleMembershipTable = new DataTable(userGroupsModal.find('#user_details_role_membership_table')[0], {
        data: entraUserDetails.transitiveMemberOf.filter(object => object["@odata.type"] == "#microsoft.graph.directoryRole"),
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'displayName', title: "Display Name" },
            { data: 'description', title: "Description" }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    userDetailsRoleMembershipTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = userDetailsRoleMembershipTable.row(tr);
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
        }
        else {
            // Open this row
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
    if ($.fn.dataTable.isDataTable(userGroupsModal.find('#user_details_owned_devices_table')[0])) {
        userGroupsModal.find('#user_details_owned_devices_table').DataTable().destroy();
        userGroupsModal.find('#user_details_owned_devices_table').empty();
    }
    let userDetailsOwnedDeviceTable = new DataTable(userGroupsModal.find('#user_details_owned_devices_table')[0], {
        data: entraUserDetails.ownedDevices,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'displayName', title: "Display Name" },
            { data: 'operatingSystem', title: "OS" },
            { data: 'profileType', title: "Type" },
            { data: 'approximateLastSignInDateTime', title: "Last Signin" }
        ],
        autoWidth: false,
        order: [[5, 'desc']]
    });
    userDetailsOwnedDeviceTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = userDetailsOwnedDeviceTable.row(tr);
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
        }
        else {
            // Open this row
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
    if ($.fn.dataTable.isDataTable(userGroupsModal.find('#user_details_app_role_assignment_table')[0])) {
        userGroupsModal.find('#user_details_app_role_assignment_table').DataTable().destroy();
        userGroupsModal.find('#user_details_app_role_assignment_table').empty();
    }
    let userDetailsAppRoleAssignmentTable = new DataTable(userGroupsModal.find('#user_details_app_role_assignment_table')[0], {
        data: entraUserDetails.appRoleAssignments,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'resourceId', title: "Resource ID", width: "320px" },
            { data: 'resourceDisplayName', title: "Resource Name" },
            { data: 'createdDateTime', title: "Created" }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    userDetailsAppRoleAssignmentTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = userDetailsAppRoleAssignmentTable.row(tr);
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
        }
        else {
            // Open this row
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
    if ($.fn.dataTable.isDataTable(userGroupsModal.find('#user_details_api_permissions_table')[0])) {
        userGroupsModal.find('#user_details_api_permissions_table').DataTable().destroy();
        userGroupsModal.find('#user_details_api_permissions_table').empty();
    }
    let userDetailsApiPermissionsTable = new DataTable(userGroupsModal.find('#user_details_api_permissions_table')[0], {
        data: entraUserDetails.oauth2PermissionGrants,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'clientId', title: "Client ID", width: "320px"},
            { data: 'resourceId', title: "App Object ID", width: "320px" },
            { data: 'scope', title: "Scope" }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    userDetailsApiPermissionsTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = userDetailsApiPermissionsTable.row(tr);
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
        }
        else {
            // Open this row
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
}

function getEntraGroupDetails(access_token_id, group_id) {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: `/api/get_entra_group_details/${encodeURIComponent(group_id)}?access_token_id=${access_token_id}`
    });
    if (response.status >= 400) {
        bootstrapToast("Get Entra ID Group Details", response.responseText, "danger");
        return;
    }
    return response.responseJSON;
}

function openGroupDetailsModal(access_token_id, group_id) {
    // Show loading cursor
    $('html, body').css('cursor', 'wait');
    let entraGroupDetails = getEntraGroupDetails(access_token_id, group_id);
    // Remove loading cursor
    $('html, body').css('cursor', '');
    if (!entraGroupDetails) {
        return;
    }
    let modalBody = `
        <div class="row ms-0" id="group_details_header_overview">
            <h5>Overview</h5>
            <ul id="group_details_overview" class="list-group">
            </ul>
        </div>
        <div class="accordion" id="groupDetailsAccordion">
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne" aria-controls="collapseOne">
                <b>Full details</b>
              </button>
            </h2>
            <div id="collapseOne" class="accordion-collapse collapse" data-bs-parent="#groupDetailsAccordion">
              <div class="accordion-body" id="group_details_full">
              </div>
            </div>
          </div>
        </div>
        <hr>
        <div class="row" id="group_details_header_members">
            <h5>Transitive Members</h5>
            <table id="group_details_transitive_members_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>User Principal Name</th>
                        <th>Mail</th>
                        <th>Type</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="group_details_header_owners">
            <h5>Owners</h5>
            <table id="group_details_owners_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>User Principal Name</th>
                        <th>Mail</th>
                        <th>Type</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="group_details_header_memberof">
            <h5>Transitive Group Membership of this Group</h5>
            <table id="group_details_transitive_memberof_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>Description</th>
                        <th>Security Enabled</th>
                        <th>Dynamic</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="group_details_header_sites">
            <h5>Sites</h5>
            <table id="group_details_sites_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Display Name</th>
                        <th>Web URL</th>
                        <th>Description</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="group_details_header_drives">
            <h5>Drives</h5>
            <table id="group_details_drives_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Name</th>
                        <th>Drive Type</th>
                        <th>Web URL</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="group_details_header_app_roles">
            <h5>App Role Assignments</h5>
            <table id="group_details_app_role_assignment_table" class="table table-striped" style="width:100%">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th>Resource ID</th>
                        <th>Resource Name</th>
                        <th>Created</th>
                    </tr>
                </thead>
            </table>
        </div>
        <hr>
        <div class="row" id="group_details_header_team">
            <h5>Team Settings</h5>
            <div id="group_details_team" class="list-group">
            </div>
        </div>
        `;
    let modalNav = `
        <nav id="entra_group_details_modal_navbar" class="navbar">
          <ul class="nav nav-pills">
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_overview">Overview</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_members">Members</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_owners">Owners</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_memberof">Member Of</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_sites">Sites</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_drives">Drives</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_app_roles">App Roles</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="#group_details_header_team">Team</a>
            </li>
          </ul>
        </nav>
        `;
    let groupDetailsModal = createModal("entra_group_details_modal", `Group details '${entraGroupDetails.displayName}'`, modalBody, "modal-xl");
    groupDetailsModal.find(".modal-title").addClass("d-inline-block text-truncate").css("max-width", "350px");
    groupDetailsModal.find(".modal-title").after(modalNav);
    groupDetailsModal.find(".modal-body").attr("data-bs-spy", "scroll").attr("data-bs-target", "#entra_group_details_modal_navbar").attr("tabindex", "0");
    groupDetailsModal.on('shown.bs.modal', function () {
        bootstrap.ScrollSpy.getOrCreateInstance(this.querySelector('.modal-body')).refresh();
    });
    groupDetailsModal.modal('show');
    function createDetailItem(key, value) {
        let item = $('<li class="list-group-item"></li>');
        item.append($('<b class="text-body-secondary"></b>').text(`${key}: `));
        item.append($('<span class="text-light-emphasis"></span>').text(value));
        return item;
    }
    let groupDetailsOverview = groupDetailsModal.find('#group_details_overview');
    groupDetailsOverview.append(createDetailItem("ID", entraGroupDetails.id));
    if (entraGroupDetails.securityIdentifier) { groupDetailsOverview.append(createDetailItem("Security ID", entraGroupDetails.securityIdentifier))};
    groupDetailsOverview.append(createDetailItem("Display Name", entraGroupDetails.displayName));
    if (entraGroupDetails.description) { groupDetailsOverview.append(createDetailItem("Description", entraGroupDetails.description))};
    if (entraGroupDetails.mail) { groupDetailsOverview.append(createDetailItem("Mail", entraGroupDetails.mail))};
    if (entraGroupDetails.mailNickname) { groupDetailsOverview.append(createDetailItem("Mail Nickname", entraGroupDetails.mailNickname))};
    groupDetailsOverview.append(createDetailItem("Mail Enabled", entraGroupDetails.mailEnabled ? "true" : "false"));
    groupDetailsOverview.append(createDetailItem("Security Enabled", entraGroupDetails.securityEnabled ? "true" : "false"));
    // Apply same group type logic as in the table
    let groupTypeLabel = "Unknown";
    if (entraGroupDetails.groupTypes && entraGroupDetails.groupTypes instanceof Array) {
        // Check if groupTypes contains "Unified"
        if (entraGroupDetails.groupTypes.includes("Unified")) {
            groupTypeLabel = "M365 Group";
        }
        // If security enabled, it's a Security Group
        else if (entraGroupDetails.securityEnabled === true) {
            groupTypeLabel = "Security Group";
        }
        // If mail enabled, but not security enabled, it's a Distribution Group
        else if (entraGroupDetails.mailEnabled === true) {
            groupTypeLabel = "Distribution Group";
        }
    }
    groupDetailsOverview.append(createDetailItem("Group Type", groupTypeLabel));
    if (entraGroupDetails.membershipRule) { groupDetailsOverview.append(createDetailItem("Membership Rule", entraGroupDetails.membershipRule))};
    if (entraGroupDetails.createdDateTime) { groupDetailsOverview.append(createDetailItem("Created", entraGroupDetails.createdDateTime))};
    if (entraGroupDetails.onPremisesSyncEnabled !== undefined) {
        groupDetailsOverview.append(createDetailItem("On-Prem Synced", entraGroupDetails.onPremisesSyncEnabled ? "true" : "false"));
        if (entraGroupDetails.onPremisesSamAccountName) { groupDetailsOverview.append(createDetailItem("On-Prem SamAccountName", entraGroupDetails.onPremisesSamAccountName))};
        if (entraGroupDetails.onPremisesDistinguishedName) { groupDetailsOverview.append(createDetailItem("On-Prem DN", entraGroupDetails.onPremisesDistinguishedName))};
        if (entraGroupDetails.onPremisesLastSyncDateTime) { groupDetailsOverview.append(createDetailItem("On-Prem Last Sync", entraGroupDetails.onPremisesLastSyncDateTime))};
        if (entraGroupDetails.onPremisesSecurityIdentifier) { groupDetailsOverview.append(createDetailItem("On-Prem SID", entraGroupDetails.onPremisesSecurityIdentifier))};
    }
    groupDetailsModal.find('#group_details_full').append(formatJsonCode(entraGroupDetails));
    Prism.highlightAll();

    // Transitive Members Table
    if ($.fn.dataTable.isDataTable(groupDetailsModal.find('#group_details_transitive_members_table')[0])) {
        groupDetailsModal.find('#group_details_transitive_members_table').DataTable().destroy();
        groupDetailsModal.find('#group_details_transitive_members_table').empty();
    }
    let transitiveMembersData = entraGroupDetails.transitiveMembers || [];
    let groupDetailsTransitiveMembersTable = new DataTable(groupDetailsModal.find('#group_details_transitive_members_table')[0], {
        data: transitiveMembersData,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'user-details-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px',
                render: function (d, t, r) {
                    if (r['@odata.type'] == "#microsoft.graph.user") {
                        return '<i class="fi fi-rr-user" style="cursor: pointer" title="View User Details"></i>';
                    }
                    return '';
                }
            },
            { data: 'displayName', title: "Display Name" },
            { data: 'userPrincipalName', title: "User Principal Name" },
            { data: 'mail', title: "Mail" },
            { 
                data: '@odata.type', 
                title: "Type",
                render: function (d, t, r) {
                    if (r['@odata.type'] == "#microsoft.graph.user") {
                        return "User";
                    } else if (r['@odata.type'] == "#microsoft.graph.group") {
                        return "Group";
                    }
                    return r['@odata.type'] || "";
                }
            }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    groupDetailsTransitiveMembersTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsTransitiveMembersTable.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
        } else {
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
    groupDetailsTransitiveMembersTable.on('click', 'td.user-details-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsTransitiveMembersTable.row(tr);
        let memberData = row.data();
        if (memberData && memberData.id && memberData['@odata.type'] == "#microsoft.graph.user") {
            openUserDetailsModal(access_token_id, memberData.id);
        }
    });

    // Owners Table
    if ($.fn.dataTable.isDataTable(groupDetailsModal.find('#group_details_owners_table')[0])) {
        groupDetailsModal.find('#group_details_owners_table').DataTable().destroy();
        groupDetailsModal.find('#group_details_owners_table').empty();
    }
    let ownersData = entraGroupDetails.owners || [];
    let groupDetailsOwnersTable = new DataTable(groupDetailsModal.find('#group_details_owners_table')[0], {
        data: ownersData,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'user-details-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px',
                render: function (d, t, r) {
                    if (r['@odata.type'] == "#microsoft.graph.user") {
                        return '<i class="fi fi-rr-user" style="cursor: pointer" title="View User Details"></i>';
                    }
                    return '';
                }
            },
            { data: 'displayName', title: "Display Name" },
            { data: 'userPrincipalName', title: "User Principal Name" },
            { data: 'mail', title: "Mail" },
            { 
                data: '@odata.type', 
                title: "Type",
                render: function (d, t, r) {
                    if (r['@odata.type'] == "#microsoft.graph.user") {
                        return "User";
                    } else if (r['@odata.type'] == "#microsoft.graph.servicePrincipal") {
                        return "Service Principal";
                    }
                    return r['@odata.type'] || "";
                }
            }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    groupDetailsOwnersTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsOwnersTable.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
        } else {
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
    groupDetailsOwnersTable.on('click', 'td.user-details-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsOwnersTable.row(tr);
        let ownerData = row.data();
        if (ownerData && ownerData.id && ownerData['@odata.type'] == "#microsoft.graph.user") {
            openUserDetailsModal(access_token_id, ownerData.id);
        }
    });

    // Transitive Member Of Table
    if ($.fn.dataTable.isDataTable(groupDetailsModal.find('#group_details_transitive_memberof_table')[0])) {
        groupDetailsModal.find('#group_details_transitive_memberof_table').DataTable().destroy();
        groupDetailsModal.find('#group_details_transitive_memberof_table').empty();
    }
    let transitiveMemberOfData = entraGroupDetails.transitiveMemberOf || [];
    let groupDetailsTransitiveMemberOfTable = new DataTable(groupDetailsModal.find('#group_details_transitive_memberof_table')[0], {
        data: transitiveMemberOfData,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'displayName', title: "Display Name" },
            { data: 'description', title: "Description" },
            { 
                data: 'securityEnabled', 
                title: "Security Enabled",
                render: function (d, t, r) {
                    return r.securityEnabled ? "true" : "false";
                }
            },
            {
                data: null,
                render: function (d, t, r) { return (r.membershipRule !== undefined && r.membershipRule !== null) ? "true" : "false"; },
                title: "Dynamic",
                width: '10px'
            }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    groupDetailsTransitiveMemberOfTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsTransitiveMemberOfTable.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
        } else {
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });

    // Drives Table
    if ($.fn.dataTable.isDataTable(groupDetailsModal.find('#group_details_drives_table')[0])) {
        groupDetailsModal.find('#group_details_drives_table').DataTable().destroy();
        groupDetailsModal.find('#group_details_drives_table').empty();
    }
    let drivesData = entraGroupDetails.drives || [];
    let groupDetailsDrivesTable = new DataTable(groupDetailsModal.find('#group_details_drives_table')[0], {
        data: drivesData,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'name', title: "Name" },
            { data: 'driveType', title: "Drive Type" },
            { 
                data: 'webUrl', 
                title: "Web URL",
                render: function (d, t, r) {
                    if (r.webUrl) {
                        return `<a href="${r.webUrl}" target="_blank">${r.webUrl}</a>`;
                    }
                    return "";
                }
            }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    groupDetailsDrivesTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsDrivesTable.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
        } else {
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });

    // Team Section
    let teamData = entraGroupDetails.team || {};
    let groupDetailsTeam = groupDetailsModal.find('#group_details_team');
    if (teamData && Object.keys(teamData).length > 0) {
        groupDetailsTeam.append(formatJsonCode(teamData));
        Prism.highlightAll();
    } else {
        groupDetailsTeam.append($('<p class="text-muted"></p>').text("No team associated with this group."));
    }

    // Sites Table
    if ($.fn.dataTable.isDataTable(groupDetailsModal.find('#group_details_sites_table')[0])) {
        groupDetailsModal.find('#group_details_sites_table').DataTable().destroy();
        groupDetailsModal.find('#group_details_sites_table').empty();
    }
    let sitesData = entraGroupDetails.sites || [];
    let groupDetailsSitesTable = new DataTable(groupDetailsModal.find('#group_details_sites_table')[0], {
        data: sitesData,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'displayName', title: "Display Name" },
            { 
                data: 'webUrl', 
                title: "Web URL",
                render: function (d, t, r) {
                    if (r.webUrl) {
                        return `<a href="${r.webUrl}" target="_blank">${r.webUrl}</a>`;
                    }
                    return "";
                }
            },
            { data: 'description', title: "Description" }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    groupDetailsSitesTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsSitesTable.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
        } else {
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });

    // App Role Assignments Table
    if ($.fn.dataTable.isDataTable(groupDetailsModal.find('#group_details_app_role_assignment_table')[0])) {
        groupDetailsModal.find('#group_details_app_role_assignment_table').DataTable().destroy();
        groupDetailsModal.find('#group_details_app_role_assignment_table').empty();
    }
    let appRoleAssignmentsData = entraGroupDetails.appRoleAssignments || [];
    let groupDetailsAppRoleAssignmentTable = new DataTable(groupDetailsModal.find('#group_details_app_role_assignment_table')[0], {
        data: appRoleAssignmentsData,
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            {
                className: 'placeholder-control',
                orderable: false,
                data: null,
                defaultContent: '',
                'width': '20px'
            },
            { data: 'resourceId', title: "Resource ID", width: "320px" },
            { data: 'resourceDisplayName', title: "Resource Name" },
            { data: 'createdDateTime', title: "Created" }
        ],
        autoWidth: false,
        order: [[2, 'asc']]
    });
    groupDetailsAppRoleAssignmentTable.on('click', 'td.dt-control', function (e) {
        let tr = e.target.closest('tr');
        let row = groupDetailsAppRoleAssignmentTable.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
        } else {
            row.child(formatJsonCode(row.data())).show();
            Prism.highlightAll();
        }
    });
}

// ========== Settings ==========

function setTableErorMessages(state) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/set_table_error_messages",
        data: { "state": state }
    });
    bootstrapToast("DataTable Error Messages", response.responseText)
    $('#dt-error-message-button-disabled').toggleClass("active")
    $('#dt-error-message-button-enabled').toggleClass("active")
}

// ========== User Agent ==========

function getUserAgent() {
    let response = $.ajax({
        type: "GET",
        async: false,
        url: "/api/get_user_agent"
    });
    if (response.status == 200) {
        return response.responseText
    }
    return "Unable to obtain user agent."
}

function setUserAgent(userAgent) {
    let response = $.ajax({
        type: "POST",
        async: false,
        url: "/api/set_user_agent",
        data: { "user_agent": userAgent }
    });
    bootstrapToast("Set User Agent", response.responseText)
}

// ========== Cookies ==========

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
};

function setCookie(name, value) {
    var today = new Date();
    var expiry = new Date(today.getTime() + 30 * 24 * 3600 * 1000);
    document.cookie = name + "=" + escape(value) + "; path=/; expires=" + expiry.toGMTString();
};

// ========== Helpers ==========

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
    } else {
        const tmp = document.createElement('TEXTAREA');
        const focus = document.activeElement;

        tmp.value = text;

        document.body.appendChild(tmp);
        tmp.select();
        document.execCommand('copy');
        document.body.removeChild(tmp);
        focus.focus();
    }
    var messageTruncated = ((text.length > 100) ? `${text.substr(0, 100)}...` : text)
    bootstrapToast("Copy to clipboard", `Copied to clipboard: '${messageTruncated}'`);
}

function reloadTables() {
    $('table.dataTable').DataTable().ajax.reload(null, false);
}

function prettifyXml(sourceXml) {
    var xmlDoc = new DOMParser().parseFromString(sourceXml, 'application/xml');
    var xsltDoc = new DOMParser().parseFromString([
        // describes how we want to modify the XML - indent everything
        '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform">',
        '  <xsl:strip-space elements="*"/>',
        '  <xsl:template match="para[content-style][not(text())]">', // change to just text() to strip space in text nodes
        '    <xsl:value-of select="normalize-space(.)"/>',
        '  </xsl:template>',
        '  <xsl:template match="node()|@*">',
        '    <xsl:copy><xsl:apply-templates select="node()|@*"/></xsl:copy>',
        '  </xsl:template>',
        '  <xsl:output indent="yes"/>',
        '</xsl:stylesheet>',
    ].join('\n'), 'application/xml');

    var xsltProcessor = new XSLTProcessor();
    xsltProcessor.importStylesheet(xsltDoc);
    var resultDoc = xsltProcessor.transformToDocument(xmlDoc);
    var resultXml = new XMLSerializer().serializeToString(resultDoc);
    if (resultXml.includes("parsererror")) {
        return sourceXml;
    }
    return resultXml;
};

function formatJsonCode(jsonInput) {
    let formatWrapper = ($('<div></div>'));
    let copyIcon = $('<i class="fi fi-rr-copy-alt float-end p-2 ms-n2" style="cursor: pointer"></i>')
    copyIcon.on('click', function () {
        copyToClipboard(JSON.stringify(jsonInput, undefined, 4));
    });
    formatWrapper.append(copyIcon);
    formatWrapper.append($('<pre></pre>').append($('<code class="language-json" style="white-space: pre-wrap; word-break: break-all"></code>').text(JSON.stringify(jsonInput, undefined, 4))));
    return formatWrapper;
}

function setButtonLoadingState(button, loadingText = "Loading...") {
    button.prop('disabled', true);
    button.find('span.spinner-border').show();
    button.find('span#button_text').text(loadingText);
}

function resetButtonState(button, originalText = "Submit") {
    button.prop('disabled', false);
    button.find('span.spinner-border').hide();
    button.find('span#button_text').text(originalText);
}

// ========== Messages ==========

function bootstrapAlert(message, type) {
    // Types: primary, secondary, success, danger, warning, info, light, dark
    var type_class = `alert-${type}`;
    var dom = $('<div>');
    dom.addClass("alert alert-dismissible");
    validTypes = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]
    if (type && validTypes.includes(type.toLowerCase())) {
        dom.addClass(`alert-${type.toLowerCase()}`);
    }
    dom.attr("role", "alert");
    dom.text(message);
    dom.append($('<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'));
    $('#alert_placeholder').append(dom);
}

function bootstrapToast(title, message, type = null, alternative = false) {
    // Types: primary, secondary, success, danger, warning, info, light, dark
    // Wrapper for new Toast Message
    var toast_wrapper = $('<div class="toast" role="alert" aria-live="assertive" aria-atomic="true"></div>');
    validTypes = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]
    if (type && validTypes.includes(type.toLowerCase())) {
        if (alternative) {
            toast_wrapper.addClass(`bg-${type.toLowerCase()}-subtle`).addClass(`text-${type.toLowerCase()}-emphasis`);
        } else {
            toast_wrapper.addClass(`text-bg-${type.toLowerCase()}`);
        }
    }
    // Toast header
    var toast_header = $('<div class="toast-header"><small>Just now</small><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div>');
    var toast_title = $('<strong class="me-auto"></strong>');
    toast_title.text(title);
    toast_header.prepend(toast_title);
    // Toast body
    var toast_body = $('<div class="toast-body"></div>');
    toast_body.text(message);
    // Append header and body to toast wrapper
    toast_wrapper.append(toast_header);
    toast_wrapper.append(toast_body);
    // Append new Toast Message to the page
    $('#toast_placeholder').append(toast_wrapper);
    // Activate the last Toast Message
    const toastList = [...$(".toast")].map(toastEl => new bootstrap.Toast(toastEl, "show"))
    toastList[toastList.length - 1].show()
}

// ========== Modals ==========

function createModal(modalID, modalTitle, modalBody, modalSize = "modal-xl") {
    // Generate unique modal ID if one with the same ID already exists
    let uniqueModalID = modalID;
    let counter = 1;
    while ($(`div.modal#${uniqueModalID}`).length > 0) {
        uniqueModalID = `${modalID}_${counter}`;
        counter++;
    }
    let modalWrapper = $(`
    <div class="modal fade" id="" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5">Temp Modal Title</h1>
                    <div class="d-flex justify-content-end align-items-center">
                        <i class="fi fi-br-expand me-2" id="expand-icon" style="cursor: pointer; opacity: 0.5"></i>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                </div>
                <div class="modal-body m-2">
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>
    `);
    modalWrapper.attr('id', uniqueModalID);
    modalWrapper.find('h1.modal-title').text(modalTitle);
    modalSize = ['modal-sm', 'modal-md', 'modal-lg', 'modal-xl'].includes(modalSize) ? modalSize : "modal-xl";
    modalWrapper.find('div.modal-dialog').addClass(modalSize);
    modalWrapper.find('div.modal-body').append(modalBody);
    modalWrapper.on('click', 'i#expand-icon', function (e) {
        $(e.target).closest(".modal-dialog").toggleClass('modal-xl').toggleClass('modal-fullscreen');
        $(e.target).toggleClass('fi-br-expand').toggleClass('fi-br-compress');
    });
    $('div#modal_container').append(modalWrapper);
    return modalWrapper;
}