# justfile for AWS Resource Visualizer
#
# オプション環境変数:
#   PROFILE            - AWSプロファイル名 (デフォルト: "dummy")
#   RAINCMD            - rainコマンド種別 (デフォルト: "rain_lint")

# local変数
PROFILE := env_var_or_default("PROFILE", "dummy")
RAINCMD := env_var_or_default("RAINCMD", "rain_lint")
STACK_PREFIX := "AwsResourceVisualizer"

# Python関連の環境変数
export PYPROJECT := `basename $PWD`
export REQUIREMENTS_TXT := "requirements.txt"

# ECR関連の環境変数
export DOCKER_IMAGE_NAME := "aws-resource-visualizer"
export DOCKER_TAG := env_var_or_default("DOCKER_TAG", "latest")
export IMAGE_NAME := DOCKER_IMAGE_NAME + ":" + DOCKER_TAG
export DOCKERFILE := "./Dockerfile"
export ECR_PROFILE := PROFILE
export ECROPT := "--no-cache"

# Rain関連の環境変数
export RAIN_CONFIG_DEFAULT_TAG := "./rainlib/rain_conf_default_tags.yml"
export RAIN_PROFILE := PROFILE

# justlibをインポート
import 'justlib/python.just'
import 'justlib/ecr.just'
import 'justlib/rain.just'
import 'justlib/act.just'

#---------------------------
# USAGE
#---------------------------

default:
    @echo "AWS Resource Visualizer - justfile"
    @echo ""
    @echo "Python開発:"
    @echo "  pyinit          - 新しいプロジェクトを初期化"
    @echo "  pyinstall       - 依存関係をインストール"
    @echo "  pylint          - コード品質チェック・型チェック"
    @echo "  pytest          - テスト実行"
    @echo "  pytest-cov      - カバレッジ付きテスト実行"
    @echo "  poetry_export   - requirements.txtを生成"
    @echo "  pyclean         - Python関連ファイルをクリーンアップ"
    @echo ""
    @echo "アプリケーション実行:"
    @echo "  run             - Streamlitアプリを起動"
    @echo "  run-debug       - デバッグモードでStreamlitアプリを起動"

    @echo ""
    @echo "Docker:"
    @echo "  docker-build    - Dockerイメージをビルド"
    @echo "  docker-run      - Dockerコンテナを起動"
    @echo "  docker-run-debug - デバッグモードでDockerコンテナを起動"
    @echo "  docker-stop     - Dockerコンテナを停止・削除"
    @echo "  docker-logs     - Dockerコンテナのログを表示"
    @echo "  docker-logs-ts  - タイムスタンプ付きでDockerコンテナのログを表示"
    @echo ""
    @echo "ECR:"
    @echo "  ecr-build       - ECR用イメージをビルド"
    @echo "  ecr-push        - ECRにイメージをプッシュ"
    @echo ""
    @echo "CloudFormation (rain):"
    @echo "  ecr             - ECRスタック操作"
    @echo "  ecs             - ECSスタック操作"
    @echo "  codepipeline    - CodePipelineスタック操作"
    @echo "  test-resources  - テストリソーススタック操作"
    @echo ""
    @echo "例:"
    @echo "  RAINCMD=rain_deploy PROFILE=sandbox just ecr"
    @echo "  RAINCMD=rain_forecast PROFILE=sandbox just ecs"

#---------------------------
# poetry環境
#---------------------------

run:
    poetry run streamlit run app_web.py

run-debug:
    STREAMLIT_LOGGER_LEVEL=debug poetry run streamlit run app_web.py

#---------------------------
# docker環境
#---------------------------

docker-build:
    just poetry_export
    hadolint ${DOCKERFILE}
    docker build --no-cache -t ${IMAGE_NAME} .

docker-run:
    docker run -d \
        --name aws-resource-visualizer \
        -p 8501:8501 \
        -e BATCH_RUN_TYPE=docker \
        -v ~/.aws:/home/appuser/.aws \
        ${IMAGE_NAME}

docker-run-debug:
    docker run -d \
        --name aws-resource-visualizer \
        -p 8501:8501 \
        -e BATCH_RUN_TYPE=docker \
        -e STREAMLIT_LOGGER_LEVEL=debug \
        -v ~/.aws:/home/appuser/.aws \
        ${IMAGE_NAME}

docker-stop:
    -docker stop aws-resource-visualizer
    -docker rm aws-resource-visualizer

docker-logs:
    docker logs -f aws-resource-visualizer

docker-logs-ts:
    docker logs -f -t aws-resource-visualizer

#---------------------------
# AWS環境
#---------------------------

# just ecr_build
ecr-build:
    just poetry_export
    just ecr_build

# PROFILE=sandbox just ecr_push
ecr-push:
    just ecr_push

# PROFILE=sandbox RAINCMD=rain_deploy just ecr
ecr:
    #!/usr/bin/env bash
    export RAIN_STACK_NAME="{{STACK_PREFIX}}-ecr"
    export RAIN_CFN_YML="cfn/cfn-ecr.yml"
    export RAIN_CONFIG="cfn/rain-ecr.yml"
    just {{RAINCMD}}

# PROFILE=sandbox RAINCMD=rain_deploy just ecs
# PROFILE=sandbox RAINCMD=rain_deploy COUNT=0 just ecs
ecs:
    #!/usr/bin/env bash
    export RAIN_STACK_NAME="{{STACK_PREFIX}}-ecs"
    export RAIN_CFN_YML="cfn/cfn-ecs.yml"
    export RAIN_CONFIG="cfn/rain-ecs.yml"
    export DESIRED_COUNT=${COUNT:-1}
    just {{RAINCMD}}

# PROFILE=sandbox RAINCMD=rain_deploy just gha-role
# TRUST_ACCOUNT_IDはssoユーザ利用前提
gha-role:
    #!/usr/bin/env bash
    export RAIN_STACK_NAME="{{STACK_PREFIX}}-gha-role"
    export RAIN_CFN_YML="cfn/cfn-gha-role.yml"
    export RAIN_CONFIG="cfn/rain-gha-role.yml"
    export TRUST_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text --profile {{PROFILE}})
    just {{RAINCMD}}

# PROFILE=sandbox RAINCMD=rain_deploy just chatbot
chatbot:
    #!/usr/bin/env bash
    export RAIN_STACK_NAME="{{STACK_PREFIX}}-chatbot"
    export RAIN_CFN_YML="cfn/cfn-chatbot.yml"
    just {{RAINCMD}}

# PROFILE=sandbox RAINCMD=rain_deploy just codepipeline
codepipeline:
    #!/usr/bin/env bash
    export RAIN_STACK_NAME="{{STACK_PREFIX}}-codepipeline"
    export RAIN_CFN_YML="cfn/cfn-codepipeline.yml"
    export RAIN_CONFIG="cfn/rain-codepipeline.yml"
    export ECS_CLUSTER_NAME="{{STACK_PREFIX}}-ecs"
    export ECS_SERVICE_NAME="{{STACK_PREFIX}}-ecs"
    just {{RAINCMD}}

# PROFILE=sandbox RAINCMD=rain_deploy just test-resources
test-resources:
    #!/usr/bin/env bash
    export RAIN_STACK_NAME="{{STACK_PREFIX}}-test-resources"
    export RAIN_CFN_YML="cfn/cfn-test-resources.yml"
    just {{RAINCMD}}

#---------------------------
# GitHub Actions
#---------------------------

# ACT_PROFILEは、前述のTRUST_ACCOUNT_IDに合わせること

# just act-ci
act-ci:
    #!/usr/bin/env bash
    export ACT_WORKFLOW="gha/app_ci.yml"
    just act-run

# PROFILE=sandbox ACT_PROFILE=sandbox just act-cd
act-cd:
    #!/usr/bin/env bash
    ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text --profile {{PROFILE}})
    export ACT_IAM_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/{{STACK_PREFIX}}-gha-role-app"
    export ACT_WORKFLOW="gha/app_cd.yml"
    just act-run

# PROFILE=sandbox ACT_PROFILE=sandbox just act-batch
act-batch:
    #!/usr/bin/env bash
    ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text --profile {{PROFILE}})
    export ACT_IAM_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/{{STACK_PREFIX}}-gha-role-batch"
    export ACT_WORKFLOW="gha/run_batch.yml"
    just act-run

# PROFILE=sandbox ACT_PROFILE=sandbox RAINCMD=rain_ls just act-rain
act-rain:
    #!/usr/bin/env bash
    ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text --profile {{PROFILE}})
    export ACT_IAM_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/{{STACK_PREFIX}}-gha-role-rain"
    export ACT_WORKFLOW="gha/rain.yml"
    echo "rain_target=${RAINCMD:-rain_lint}" > .input
    echo "ecr_tag={{DOCKER_TAG}}" >> .input
    echo "desired_count=${COUNT:-0}" >> .input
    just act-run || true
    rm -rf .input

# just act-install
gha-install:
    #!/usr/bin/env bash
    cp gha/app_ci.yml .github/workflows/.
    cp gha/app_cd.yml .github/workflows/.
    cp gha/run_batch.yml .github/workflows/.
    cp gha/rain.yml .github/workflows/.

#---------------------------
# SSM Parameter Store
#---------------------------

# PROFILE=sandbox just ssm-put-rainlib
ssm-put-rainlib:
    #!/usr/bin/env bash
    echo "rainlib/*.ymlファイルをSSMパラメータストアに登録中..."
    for file in rainlib/*.yml; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            parameter_name="/resources-visualiser/rainlib/$filename"
            echo "登録中: $parameter_name"
            aws ssm put-parameter \
                --name "$parameter_name" \
                --value "$(cat "$file")" \
                --type "String" \
                --overwrite \
                --profile {{PROFILE}}
        fi
    done
    echo "完了しました。"

# PROFILE=sandbox just ssm-get-rainlib
ssm-get-rainlib:
    #!/usr/bin/env bash
    echo "SSMパラメータストアからrainlibファイルを取得中..."
    aws ssm get-parameters-by-path \
        --path "/resources-visualiser/rainlib/" \
        --recursive \
        --query 'Parameters[*].[Name,Value]' \
        --output table \
        --profile {{PROFILE}}

# PROFILE=sandbox just ssm-delete-rainlib
ssm-delete-rainlib:
    #!/usr/bin/env bash
    echo "SSMパラメータストアからrainlibパラメータを削除中..."
    parameters=$(aws ssm get-parameters-by-path \
        --path "/resources-visualiser/rainlib/" \
        --recursive \
        --query 'Parameters[*].Name' \
        --output text \
        --profile {{PROFILE}})

    if [ -n "$parameters" ]; then
        for param in $parameters; do
            echo "削除中: $param"
            aws ssm delete-parameter \
                --name "$param" \
                --profile {{PROFILE}}
        done
        echo "削除完了しました。"
    else
        echo "削除対象のパラメータが見つかりませんでした。"
    fi

# just ssm-download-rainlib
# GithubActions(rain.yml)用なのでprofileは指定しない
ssm-download-rainlib:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "SSMパラメータストアからrainlibファイルをダウンロード中..."

    # パラメータ名のリストを取得
    param_names=$(aws ssm get-parameters-by-path \
        --path "/resources-visualiser/rainlib/" \
        --recursive \
        --query 'Parameters[].Name' \
        --output text)

    # 各パラメータを個別に取得してファイルに保存
    for param_name in $param_names; do
        filename=$(basename "$param_name")
        filepath="rainlib/$filename"
        echo "ダウンロード中: $param_name -> $filepath"

        aws ssm get-parameter \
            --name "$param_name" \
            --query 'Parameter.Value' \
            --output text > "$filepath"
    done

    echo "ダウンロード完了しました。"
