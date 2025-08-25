# Rain command utilities
#
# 必須環境変数:
#   RAIN_STACK_NAME     - CloudFormationスタック名
#   RAIN_CFN_YML        - CloudFormationテンプレートファイルパス
#   RAIN_CONFIG_DEFAULT_TAG - デフォルトタグ設定ファイルパス
#   RAIN_PROFILE        - AWSプロファイル名
#
# オプション環境変数:
#   RAIN_CONFIG         - 追加設定ファイルパス (デフォルト: 空文字列)
#   RAINPKGOPT          - rain pkgオプション (デフォルト: 空文字列)
#   RAINOPT             - rainコマンドオプション (デフォルト: 空文字列 )
#   RAINDIFFOPT         - rain diffオプション (デフォルト: 空文字列)

_rain_msg_info message:
    #!/usr/bin/env bash
    echo -e "\033[32m*🌂* rain.just * {{message}}\033[0m"

_rain_msg_err message:
    #!/usr/bin/env bash
    echo -e "\033[31m*☔* rain.just * Error: {{message}}\033[0m"

_rain_create_tmp:
    #!/usr/bin/env bash
    set -euo pipefail

    RAIN_TEMPLATE_TMP="${RAIN_STACK_NAME}.tmpl.raintmp.yml"
    RAIN_CONFIG_TMP="${RAIN_STACK_NAME}.conf.raintmp.yml"

    if [ -e "${RAIN_TEMPLATE_TMP}" ]; then
        echo -e "\033[31m*☔* rain.just * Error: ${RAIN_TEMPLATE_TMP} already exists. run 'just rain_clean'.\033[0m"
        exit 1
    fi

    if [ -e "${RAIN_CONFIG_TMP}" ]; then
        echo -e "\033[31m*☔* rain.just * Error: ${RAIN_CONFIG_TMP} already exists. run 'just rain_clean'.\033[0m"
        exit 1
    fi

    echo -e "\033[32m*🌂* rain.just * run rain pkg.\033[0m"
    if ! rain pkg ${RAIN_CFN_YML} --no-analytics -o ${RAIN_TEMPLATE_TMP} ${RAINPKGOPT:-}; then
        echo -e "\033[31m*☔* rain.just * Error: rain pkg failed.\033[0m"
        exit 1
    fi

    echo -e "\033[32m*🌂* rain.just * run cfn-lint.\033[0m"
    if ! cfn-lint ${RAIN_TEMPLATE_TMP}; then
        echo -e "\033[31m*☔* rain.just * Error: cfn-lint failed.\033[0m"
        exit 1
    fi

    if ! envsubst < ${RAIN_CONFIG_DEFAULT_TAG} > ${RAIN_CONFIG_TMP}; then
        echo -e "\033[31m*☔* rain.just * Error: envsubst failed. ${RAIN_CONFIG_DEFAULT_TAG}\033[0m"
        exit 1
    fi

    if [ -n "${RAIN_CONFIG:-}" ]; then
        if ! envsubst < "${RAIN_CONFIG}" >> ${RAIN_CONFIG_TMP}; then
            echo -e "\033[31m*☔* rain.just * Error: envsubst failed. ${RAIN_CONFIG}\033[0m"
            exit 1
        fi
    fi

    echo -e "\033[32m*🌂* rain.just * print rain config.\033[0m"
    cat ${RAIN_CONFIG_TMP}

rain_lint:
    @just _rain_msg_info "Lint the CloudFormation template."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_create_tmp
    @just _rain_msg_info "run rain."
    rain fmt ${RAIN_STACK_NAME}.tmpl.raintmp.yml ${RAINOPT:-}
    @just rain_clean

rain_forecast:
    @just _rain_msg_info "Show the forecast of stack changes."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_create_tmp
    @just _rain_msg_info "run rain."
    rain forecast ${RAIN_STACK_NAME}.tmpl.raintmp.yml ${RAIN_STACK_NAME} ${RAINOPT:-} \
        --experimental \
        --profile ${RAIN_PROFILE} \
        --config ${RAIN_STACK_NAME}.conf.raintmp.yml
    @just rain_clean

rain_deploy:
    @just _rain_msg_info "Deploy the stack."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_create_tmp
    @just _rain_msg_info "run rain."
    rain deploy ${RAIN_STACK_NAME}.tmpl.raintmp.yml ${RAIN_STACK_NAME} ${RAINOPT:-} \
        --profile ${RAIN_PROFILE} \
        --config ${RAIN_STACK_NAME}.conf.raintmp.yml
    @just rain_clean

rain_rm:
    @just _rain_msg_info "Remove the stack."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_msg_info "run rain."
    rain rm ${RAIN_STACK_NAME} ${RAINOPT:-} \
        --profile ${RAIN_PROFILE}

rain_diff:
    @just _rain_msg_info "Compare local and deployed stack."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_create_tmp
    @just _rain_msg_info "run rain."
    @just _rain_diff_exe
    @just rain_clean

_rain_diff_exe:
    #!/usr/bin/env bash
    rain diff <(rain cat ${RAIN_STACK_NAME} --profile ${RAIN_PROFILE} ${RAINOPT:-}) \
        ${RAIN_STACK_NAME}.tmpl.raintmp.yml ${RAINDIFFOPT:-}

rain_ls:
    @just _rain_msg_info "Show stack information."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_msg_info "run rain."
    rain ls ${RAIN_STACK_NAME} ${RAINOPT:-} \
        --profile ${RAIN_PROFILE}

rain_logs:
    @just _rain_msg_info "Show stack logs."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_msg_info "run rain."
    rain logs ${RAIN_STACK_NAME} ${RAINOPT:-} \
        --all \
        --profile ${RAIN_PROFILE}

rain_tree:
    @just _rain_msg_info "Show stack resource tree."
    @just _rain_msg_info "print stack name."
    @echo "${RAIN_STACK_NAME}"
    @just _rain_create_tmp
    @just _rain_msg_info "run rain."
    rain tree ${RAIN_STACK_NAME}.tmpl.raintmp.yml ${RAINOPT:-}
    @just rain_clean

rain_info:
    @just _rain_msg_info "Display the AWS account and region."
    @just _rain_msg_info "run rain."
    rain info ${RAINOPT:-} \
        --profile ${RAIN_PROFILE}

rain_clean:
    rm -f *.raintmp.yml
