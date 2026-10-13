`default_nettype none

module spi_peripheral (
    input wire clk,
    input wire rst_n,

    input wire sclk,
    input wire copi,
    input wire ncs,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

    reg sclk_meta, sclk_sync;
    reg copi_meta, copi_sync;
    reg ncs_meta, ncs_sync;

    // Synchronize the SPI signals to the system clock domain
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_meta <= 1'b0;
            sclk_sync <= 1'b0;
            copi_meta <= 1'b0;
            copi_sync <= 1'b0;
            ncs_meta <= 1'b1;
            ncs_sync <= 1'b1;
        end else begin
            sclk_meta <= sclk;
            sclk_sync <= sclk_meta;
            copi_meta <= copi;
            copi_sync <= copi_meta;
            ncs_meta <= ncs;
            ncs_sync <= ncs_meta;
        end
    end

    reg sclk_prev;
    reg ncs_prev;

    // Detect edges of SCLK and NCS 
    always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                sclk_prev <= 1'b0;
                ncs_prev <=  1'b1;
            end else begin
                sclk_prev <= sclk_sync;
                ncs_prev <= ncs_sync;
            end
    end

    wire sclk_rise = sclk_sync && !sclk_prev; // Detect rising edge of SCLK
    wire ncs_fall = !ncs_sync && ncs_prev; // Detect falling edge of NCS
    wire ncs_rise = ncs_sync && !ncs_prev; // Detect rising edge of NCS

    reg [15:0] shift_reg;
    reg [4:0] bit_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg <= 16'b0;
            bit_count <= 5'b0;
        end else if (ncs_fall) begin
            //Clear storage for new transcation
            shift_reg <= 16'b0;
            bit_count <= 5'b0;
        end else if (!ncs_sync && sclk_rise && bit_count < 5'd16) begin
            //Capture one bit on a detected rising edgle of SCLK while NCS is low
            shift_reg <= {shift_reg[14:0], copi_sync};
            bit_count <= bit_count + 5'd1;
        end 
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            en_reg_out_7_0 <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0 <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle <= 8'b0;
        end else if (ncs_rise && bit_count == 5'd16 && shift_reg[15]) begin
            //Write recieved data into addressed register when chip select rises
            case (shift_reg[14:8])
                7'h00: en_reg_out_7_0 <= shift_reg[7:0];
                7'h01: en_reg_out_15_8 <= shift_reg[7:0];
                7'h02: en_reg_pwm_7_0 <= shift_reg[7:0];
                7'h03: en_reg_pwm_15_8 <= shift_reg[7:0];
                7'h04: pwm_duty_cycle <= shift_reg[7:0];
                default: begin
                  // Do nothing for unrecognized addresses
                end 
            endcase
        end
    end


endmodule